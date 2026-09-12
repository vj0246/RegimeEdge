"""Phase 3 detector validation (decisions.md section 12): synthetic delay and false-alarm curves, and
rolling-refit stability on development data.

  python -m osr.validation synthetic [--paths 100] [--workers N]
  python -m osr.validation stability
"""

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from arch import arch_model
from sklearn.metrics import adjusted_rand_score

from osr import synthetic
from osr.config import settings
from osr.data.rates import daily_cash_return
from osr.detectors.base import gate_path, majority_filter
from osr.detectors.bocpd import BOCPDGate
from osr.detectors.features import detector_inputs
from osr.detectors.hmm import HMMGate
from osr.detectors.jump import JumpGate
from osr.detectors.threshold import PercentileGate

DEV_START, DEV_END = pd.Timestamp("1995-11-03"), pd.Timestamp("2007-12-31")
WINDOW, MIN_HISTORY = 3000, 1500
SYN_DAYS, SYN_REFIT_EVERY = 6000, 250
PROB_CUTS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
PERCENTILES = (70.0, 75.0, 80.0, 85.0, 90.0, 95.0)
JM_PENALTIES = (10.0, 50.0, 200.0)


def detection_stats(gate: np.ndarray, states: np.ndarray | None) -> dict[str, float]:
    """Time flat and switches a year. With true states, also detection delay (trading days from an episode's
    start to the first stressed signal inside it), miss rate, and false alarms (rises during calm) a calm year."""
    live = ~np.isnan(gate)
    g = gate[live].astype(int)
    out = {"flat_share": g.mean(), "switches_per_year": np.abs(np.diff(g)).sum() / (len(g) / 252)}
    if states is None:
        return out
    s = states[live]
    delays = []
    for i0 in np.flatnonzero((s[1:] == 1) & (s[:-1] == 0)) + 1:
        calm = np.flatnonzero(s[i0:] == 0)
        hits = np.flatnonzero(g[i0 : i0 + calm[0] if len(calm) else len(s)] == 1)
        delays.append(hits[0] if len(hits) else np.nan)
    d = np.asarray(delays, dtype=float)
    rises = np.flatnonzero((g[1:] == 1) & (g[:-1] == 0)) + 1
    out.update({
        "episodes": len(d),
        "miss_rate": np.isnan(d).mean() if len(d) else np.nan,
        "delay_median": np.nanmedian(d) if np.isfinite(d).any() else np.nan,
        "false_alarms_per_year": (s[rises] == 0).sum() / ((s == 0).sum() / 252),
    })
    return out


def percentile_sweep(make, x: pd.DataFrame, refits, qs, window: int = WINDOW,
                     min_history: int = MIN_HISTORY) -> dict[float, pd.Series]:
    """Gates at several fit-window percentiles of a detector's score, one fit per refit."""
    pos = sorted(x.index.get_indexer(pd.DatetimeIndex(refits)))
    if pos[0] < 0:
        raise ValueError("every refit date must be a row of x")
    out = {q: pd.Series(np.nan, index=x.index, name="gate") for q in qs}
    for p, nxt in zip(pos, [*pos[1:], len(x)]):
        start = max(0, p + 1 - window)
        if p + 1 - start < min_history:
            continue
        det = make()
        det.fit(x.iloc[start : p + 1])
        score = det.score(x.iloc[start:nxt])
        for q in qs:
            out[q].iloc[p:nxt] = (score[p - start :] > np.percentile(score[: p + 1 - start], q)).astype(float)
    return out


def refit_stability(make, x: pd.DataFrame, refits, window: int = WINDOW, min_history: int = MIN_HISTORY) -> pd.DataFrame:
    """Adjusted Rand index and share of reclassified days between consecutive refits' in-sample stressed
    paths, on the days both windows cover. ARI ignores label names; the flip rate does not."""
    rows, prev = [], None
    for p in sorted(x.index.get_indexer(pd.DatetimeIndex(refits))):
        start = max(0, p + 1 - window)
        if p + 1 - start < min_history:
            continue
        det = make()
        det.fit(x.iloc[start : p + 1])
        cur = (start, p, det.insample_stressed(x.iloc[start : p + 1]))
        if prev is not None:
            prev_start, prev_end, prev_path = prev
            a = prev_path[start - prev_start : prev_end - prev_start + 1]
            b = cur[2][: prev_end - start + 1]
            rows.append({"date": x.index[p], "ari": adjusted_rand_score(a, b),
                         "flip_rate": float(np.mean(a != b)), "overlap": len(a)})
        prev = cur
    return pd.DataFrame(rows)


def path_results(r: pd.Series, states: pd.Series | None) -> list[dict]:
    x = detector_inputs(r)
    st = None if states is None else states.reindex(x.index).to_numpy()
    refits = list(x.index[MIN_HISTORY - 1 :: SYN_REFIT_EVERY])
    rows = []

    def add(detector: str, param: float, gate: pd.Series) -> None:
        rows.append({"detector": detector, "param": param, **detection_stats(gate.to_numpy(), st)})

    prob = gate_path(lambda: HMMGate(2), x, refits, WINDOW, MIN_HISTORY, method="score")
    for c in PROB_CUTS:
        raw = (prob > c).astype(float).where(prob.notna())
        add("HMM-2", c, raw)
        add("HMM-2 k20", c, majority_filter(raw, 20))
    for name, make in (("RV", lambda: PercentileGate("rv")), ("BOCPD", BOCPDGate)):
        for q, gate in percentile_sweep(make, x, refits, PERCENTILES).items():
            add(name, q, gate)
    for lam in JM_PENALTIES:
        add("JM", lam, gate_path(lambda lam=lam: JumpGate(lam), x, refits, WINDOW, MIN_HISTORY))
    return rows


def run_path(task: tuple[str, dict, int]) -> list[dict]:
    dgp, params, seed = task
    if dgp == "hmm":
        r, states = synthetic.simulate_hmm(SYN_DAYS, params["means"], params["sds"], params["transmat"], seed=seed)
    elif dgp == "hsmm_t":
        r, states = synthetic.simulate_hsmm_t(SYN_DAYS, params["means"], params["sds"], params["durations"], seed=seed)
    else:
        r, states = synthetic.simulate_garch_t(SYN_DAYS, **params, seed=seed), None
    return [{"dgp": dgp, "seed": seed, **row} for row in path_results(r, states)]


def dev_returns() -> pd.Series:
    """NIFTY 50 daily log returns, development period only."""
    close = pd.read_parquet(settings.data_dir / "processed" / "nifty50_price.parquet").set_index("date")["close"]
    close = close[(close.index >= DEV_START) & (close.index <= DEV_END)]
    return np.log(close).diff().dropna()


def fit_dgps(r: pd.Series) -> dict[str, dict]:
    """DGP parameters from development-period daily log returns; state 0 is the calm state."""
    hmm = HMMGate(2)
    hmm.fit(pd.DataFrame({"r": r}))
    order = np.argsort(hmm.sd)
    trans = np.exp(hmm.log_trans)[np.ix_(order, order)]
    means, sds = hmm.mean[order] / hmm.scale, hmm.sd[order] / hmm.scale
    g = arch_model(100 * r, mean="Constant", vol="GARCH", p=1, q=1, dist="t").fit(disp="off").params
    return {
        "hmm": {"means": means.tolist(), "sds": sds.tolist(), "transmat": trans.tolist()},
        "hsmm_t": {"means": means.tolist(), "sds": sds.tolist(), "durations": (1 / (1 - np.diag(trans))).tolist()},
        "garch_t": {"mu": g["mu"], "omega": g["omega"], "alpha": g["alpha[1]"], "beta": g["beta[1]"], "nu": g["nu"]},
    }


def monthly_expiries() -> pd.DatetimeIndex:
    panel = pd.read_parquet(settings.data_dir / "processed" / "nifty_fo.parquet", columns=["instrument", "expiry"])
    return pd.DatetimeIndex(sorted(panel.loc[panel["instrument"] == "FUT", "expiry"].unique()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["synthetic", "stability"])
    parser.add_argument("--paths", type=int, default=100)
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    args = parser.parse_args()
    out = settings.data_dir / "results"
    out.mkdir(parents=True, exist_ok=True)

    if args.what == "synthetic":
        params = fit_dgps(dev_returns())
        (out / "synthetic_dgp_params.json").write_text(json.dumps(params, indent=2))
        tasks = [(dgp, params[dgp], seed) for dgp in params for seed in range(args.paths)]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            df = pd.DataFrame([row for rows in pool.map(run_path, tasks) for row in rows])
        df.to_parquet(out / "validation_synthetic.parquet", index=False)
        summary = df.groupby(["dgp", "detector", "param"]).mean(numeric_only=True).drop(columns="seed")
        print(summary.round(3).to_string())
    else:
        r = dev_returns()
        x = detector_inputs(r, daily_cash_return(pd.read_parquet(settings.data_dir / "processed" / "tbill91.parquet"),
                                                 r.index))
        refits = [d for d in monthly_expiries() if d in x.index and d <= DEV_END]
        makes = {"HMM-2": lambda: HMMGate(2), "HMM-3": lambda: HMMGate(3), "JM": lambda: JumpGate(50.0),
                 "BOCPD": BOCPDGate, "RV": lambda: PercentileGate("rv")}
        df = pd.concat([refit_stability(m, x, refits).assign(detector=n) for n, m in makes.items()], ignore_index=True)
        df.to_csv(out / "stability_dev.csv", index=False)
        print(df.groupby("detector")[["ari", "flip_rate"]].agg(["mean", "min", "max"]).round(3).to_string())


if __name__ == "__main__":
    main()
