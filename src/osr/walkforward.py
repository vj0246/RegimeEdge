"""Walk-forward runner (decisions.md sections 2 to 11): gate paths, both tracks, metrics, ledger.

  python -m osr.walkforward dev      development period; no input row after 2007-12-31 is loaded
  python -m osr.walkforward sealed   the pre-registered run; refuses unless prereg.lock verifies
"""

import argparse
import hashlib
import logging
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from osr import lock, report
from osr.config import settings
from osr.data.rates import daily_cash_return
from osr.detectors.base import gate_path, majority_filter
from osr.detectors.bocpd import BOCPDGate
from osr.detectors.features import detector_inputs
from osr.detectors.hmm import HMMGate
from osr.detectors.jump import JumpGate
from osr.detectors.threshold import PercentileGate
from osr.engine import ledger, stats
from osr.engine.costs import HALF_SPREAD, TRI_TIERS
from osr.strategies import straddle
from osr.strategies.tri import tri_returns

DETECTOR_START, OPTIONS_START = pd.Timestamp("1995-11-03"), pd.Timestamp("2004-01-01")
DEV_END, SEALED_START, SAMPLE_CAP = pd.Timestamp("2007-12-31"), pd.Timestamp("2008-01-01"), pd.Timestamp("2026-08-31")
JM_PENALTIES = (1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0)
SMOOTH_K = 20  # majority filter applied to every gate (decisions.md 8.8)
JM_VALIDATION = pd.DateOffset(years=8)
JM_MIN_VALIDATION_DAYS = 3 * 252
IV_MIN_HISTORY = 250
LAGS = (1, 2)
PANEL_COLUMNS = ["date", "instrument", "expiry", "strike", "opt_type", "close", "settle", "volume"]
NEAR_DAYS = 70


@dataclass(frozen=True)
class Inputs:
    x: pd.DataFrame
    rf: pd.Series
    tri: pd.Series
    panel: pd.DataFrame
    auctions: pd.DataFrame
    expiries: pd.DatetimeIndex


def load_inputs(end: pd.Timestamp) -> Inputs:
    """Everything a run needs, with no row dated after `end`."""
    p = settings.data_dir / "processed"
    close = pd.read_parquet(p / "nifty50_price.parquet").set_index("date")["close"]
    close = close[(close.index >= DETECTOR_START) & (close.index <= end)]
    auctions = pd.read_parquet(p / "tbill91.parquet")
    auctions = auctions[auctions["date"] <= end]
    rf = daily_cash_return(auctions, close.index).fillna(0.0)
    x = detector_inputs(np.log(close).diff().dropna(), rf)
    tri = pd.read_parquet(p / "nifty50_tri.parquet").set_index("date")["tri"]
    fo = p / "nifty_fo.parquet"
    fut = pd.read_parquet(fo, columns=PANEL_COLUMNS, filters=[("instrument", "==", "FUT"), ("date", "<=", end)])
    monthly = [pd.Timestamp(e) for e in sorted(fut["expiry"].unique())]
    # Memory: only monthly contracts within NEAR_DAYS of expiry are ever used (cycle legs expire within about 36
    # days of entry; the IV contract within 42 days), so weeklies and long-dated rows are dropped at load.
    opt = pd.read_parquet(fo, columns=PANEL_COLUMNS,
                          filters=[("instrument", "==", "OPT"), ("date", "<=", end), ("expiry", "in", monthly)])
    opt = opt[(opt["expiry"] - opt["date"]).dt.days <= NEAR_DAYS]
    panel = pd.concat([fut, opt], ignore_index=True)
    expiries = straddle.monthly_expiries(panel)
    return Inputs(x, rf, tri[tri.index <= end], panel, auctions, expiries[expiries <= end])


def run_gate(task: tuple[str, pd.DataFrame, list, float | None]) -> tuple[str, pd.Series]:
    name, x, refits, penalty = task
    makers = {"HMM-2": lambda: HMMGate(2), "HMM-3": lambda: HMMGate(3), "BOCPD": BOCPDGate,
              "RV": lambda: PercentileGate("rv")}
    make = (lambda: JumpGate(penalty)) if penalty is not None else makers[name]
    return name, gate_path(make, x, refits)


def select_jm(paths: dict[float, pd.Series], tri: pd.Series, rf: pd.Series, selection_dates,
              validation=JM_VALIDATION, min_days: int = JM_MIN_VALIDATION_DAYS) -> tuple[pd.Series, pd.Series]:
    """At each selection date, the penalty whose Track T gate (headline costs, 1-day lag) had the best
    trailing Sharpe ratio; its gate is used until the next selection date (decisions.md 8.3)."""
    rf_tri = rf.reindex(tri.index).fillna(0.0)
    excess = pd.DataFrame({lam: tri_returns(tri, rf_tri, g, 1, *TRI_TIERS["headline"]) - rf_tri
                           for lam, g in paths.items()})
    index = next(iter(paths.values())).index
    live_from = max(g.first_valid_index() for g in paths.values())
    gate, chosen = pd.Series(np.nan, index=index, name="gate"), pd.Series(np.nan, index=index, name="penalty")
    dates = [d for d in selection_dates if d in index]
    for e, nxt in zip(dates, [*dates[1:], None]):
        window = excess.loc[max(e - validation, live_from) : e].dropna()
        if len(window) < min_days:
            continue
        best = (window.mean() / window.std()).idxmax()
        days = index[(index >= e) & ((index < nxt) if nxt is not None else True)]
        gate[days], chosen[days] = paths[best][days], best
    return gate, chosen


def all_gates(inp: Inputs, workers: int) -> tuple[dict[str, pd.Series], pd.Series]:
    """Every gate, smoothed by the majority filter; JM penalty candidates are smoothed before selection."""
    refits = [e for e in inp.expiries if e in inp.x.index]
    half_year = [e for e in refits if e.month in (1, 7)]
    tasks = [(name, inp.x, refits, None) for name in ("HMM-2", "HMM-3", "BOCPD", "RV")]
    tasks += [(f"JM {lam:g}", inp.x, half_year, lam) for lam in JM_PENALTIES]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        paths = {k: majority_filter(v, SMOOTH_K) for k, v in pool.map(run_gate, tasks)}
    gates = {k: v for k, v in paths.items() if not k.startswith("JM ")}
    jm_paths = {float(k.split()[1]): v for k, v in paths.items() if k.startswith("JM ")}
    gates["JM"], chosen = select_jm(jm_paths, inp.tri, inp.rf, refits)
    iv = straddle.atm_iv(inp.panel[inp.panel["date"] >= OPTIONS_START], inp.auctions).dropna()
    iv_gate = gate_path(lambda: PercentileGate("iv"), iv.to_frame("iv"), [e for e in refits if e in iv.index],
                        window=None, min_history=IV_MIN_HISTORY)
    gates["IV"] = majority_filter(iv_gate, SMOOTH_K)
    return gates, chosen


def period_plan(inp: Inputs, start: pd.Timestamp) -> straddle.Plan:
    sub = inp.panel[inp.panel["date"] >= start]
    return straddle.build_plan(sub, daily_cash_return(inp.auctions, pd.DatetimeIndex(sorted(sub["date"].unique()))))


def period_returns(inp: Inputs, gates: dict[str, pd.Series], plan: straddle.Plan, start: pd.Timestamp,
                   end: pd.Timestamp, lag: int, tier: str, half_spread: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Daily returns of every family member, from the first day on which every gate has a signal."""
    rf_tri = inp.rf.reindex(inp.tri.index).fillna(0.0)
    t_gates = {k: v for k, v in gates.items() if k != "IV"}
    t_ret = pd.DataFrame({"ungated": tri_returns(inp.tri, rf_tri),
                          **{k: tri_returns(inp.tri, rf_tri, g, lag, *TRI_TIERS[tier]) for k, g in t_gates.items()}})
    s_ret = pd.DataFrame({"ungated": straddle.simulate(plan, None, lag, half_spread),
                          **{k: straddle.simulate(plan, g.reindex(plan.dates).to_numpy(), lag, half_spread)
                             for k, g in gates.items()}})
    lo = max(start, *(g.first_valid_index() for g in gates.values()))
    return t_ret.loc[lo:end], s_ret.loc[lo:end]


def record(out: Path, name: str, returns: pd.DataFrame, rf: pd.Series, config: dict, manifest_sha: str) -> pd.DataFrame:
    """Save one run's daily returns under its own run folder and add a ledger row per family member."""
    path = out / f"{name}.parquet"
    returns.to_parquet(path)
    f = rf.reindex(returns.index).fillna(0.0).to_numpy()
    rows = {}
    for member in returns:
        rows[member] = stats.summary(returns[member].to_numpy(), f)
        ledger.append({**config, "member": member}, manifest_sha, str(path), rows[member])
    return pd.DataFrame(rows).T


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("period", choices=["dev", "sealed"])
    parser.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    args = parser.parse_args()

    if args.period == "sealed":
        lock.verify()
        panel_expiries = straddle.monthly_expiries(pd.read_parquet(settings.data_dir / "processed" / "nifty_fo.parquet",
                                                                   columns=["instrument", "expiry"]))
        start, end = SEALED_START, panel_expiries[panel_expiries <= SAMPLE_CAP][-1]
    else:
        start, end = OPTIONS_START, DEV_END
    manifest_sha = hashlib.sha256((settings.data_dir / "manifest.json").read_bytes()).hexdigest()
    inp = load_inputs(end)
    gates, chosen = all_gates(inp, args.workers)
    plan = period_plan(inp, start)
    inp = replace(inp, panel=inp.panel.iloc[:0])  # the panel is not needed after the plan and IV
    run_id = pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")
    out = settings.data_dir / "results" / args.period / run_id
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({**gates, "jm_penalty": chosen}).to_parquet(out / "gates.parquet")
    logging.info("run %s", out)

    for lag in LAGS:
        for tier, spread in zip(("headline", "delivery", "stress"), ("headline", "low", "high")):
            t_ret, s_ret = period_returns(inp, gates, plan, start, end, lag, tier, HALF_SPREAD[spread])
            base = {"period": args.period, "run_id": run_id, "lag": lag, "smooth_k": SMOOTH_K,
                    "jm_penalties": JM_PENALTIES}
            rf_s = pd.Series(plan.rf, index=plan.dates)
            t_tab = record(out, f"trackT_lag{lag}_{tier}", t_ret, inp.rf, {**base, "track": "T", "tier": tier}, manifest_sha)
            s_tab = record(out, f"trackS_lag{lag}_{spread}", s_ret, rf_s, {**base, "track": "S", "spread": spread}, manifest_sha)
            if lag == 1 and tier == "headline":
                print(f"\nTrack T, {t_ret.index[0].date()} to {t_ret.index[-1].date()}\n{t_tab.round(3).to_string()}")
                print(f"\nTrack S, {s_ret.index[0].date()} to {s_ret.index[-1].date()}\n{s_tab.round(3).to_string()}")
                report.run(out, inp, gates, t_ret, s_ret, plan, rf_s, lag, tier, HALF_SPREAD[spread])


if __name__ == "__main__":
    main()
