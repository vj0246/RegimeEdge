"""Phase 4 checks on development data (PLAN.md section 4).

  python -m osr.checks straddle 2004-05-17 [...]   the cycles containing these days, by hand from raw rows vs the engine
  python -m osr.checks null                                   circular-shift p-values of uninformative gates
"""

import argparse
import json
from datetime import date

import numpy as np
import pandas as pd

from osr import synthetic
from osr.config import settings
from osr.data.dates import format_day_mon_year
from osr.data.nse_fo import raw_path
from osr.engine import stats
from osr.engine.costs import OPT_SELL, TRI_TIERS
from osr.strategies import straddle
from osr.strategies.tri import tri_returns

DEV_END = pd.Timestamp("2007-12-31")


def raw_rows(d: date) -> pd.DataFrame:
    """One day's NIFTY rows from the raw old-format bhavcopy, without the normaliser."""
    df = pd.read_csv(raw_path(settings.data_dir, d), dtype=str)
    df = df.rename(columns={"OPTIONTYPE": "OPTION_TYP"})
    df[["STRIKE_PR", "CLOSE", "SETTLE_PR", "CONTRACTS"]] = df[["STRIKE_PR", "CLOSE", "SETTLE_PR", "CONTRACTS"]].astype(float)
    df["EXPIRY_DT"] = df["EXPIRY_DT"].str.upper()
    return df


def straddle_by_hand(entry: date, expiry: date, half_spread: float) -> tuple[float, dict]:
    """Ungated cycle return with zero cash rate, from the entry and expiry files only."""
    exp = format_day_mon_year(expiry).upper()
    on_entry, on_expiry = raw_rows(entry), raw_rows(expiry)
    fwd = on_entry[(on_entry["INSTRUMENT"] == "FUTIDX") & (on_entry["EXPIRY_DT"] == exp)]["SETTLE_PR"].iloc[0]
    opt = on_entry[(on_entry["INSTRUMENT"] == "OPTIDX") & (on_entry["EXPIRY_DT"] == exp) & (on_entry["CONTRACTS"] > 0)]
    calls = opt[opt["OPTION_TYP"] == "CE"].set_index("STRIKE_PR")["CLOSE"]
    puts = opt[opt["OPTION_TYP"] == "PE"].set_index("STRIKE_PR")["CLOSE"]
    strike = min(set(calls.index) & set(puts.index), key=lambda k: (abs(k - fwd), k))
    settle = on_expiry[(on_expiry["INSTRUMENT"] == "FUTIDX") & (on_expiry["EXPIRY_DT"] == exp)]["SETTLE_PR"].iloc[0]
    units = 1 / fwd
    final = 1 + units * (calls[strike] + puts[strike]) * (1 - OPT_SELL - half_spread) - units * abs(settle - strike)
    return final - 1, {"forward": fwd, "strike": strike, "call": calls[strike], "put": puts[strike], "settlement": settle}


def straddle_by_engine(panel: pd.DataFrame, entry: date, expiry: date, half_spread: float) -> float:
    previous = straddle.monthly_expiries(panel)
    previous = previous[previous < pd.Timestamp(entry)][-1]
    sub = panel[(panel["date"] >= previous) & (panel["date"] <= pd.Timestamp(expiry))]
    plan = straddle.build_plan(sub, pd.Series(0.0, index=pd.DatetimeIndex(sorted(sub["date"].unique()))))
    r = straddle.simulate(plan, None, half_spread=half_spread)
    return float(np.prod(1 + r.loc[pd.Timestamp(entry) :]) - 1)


def null_calibration(n_gates: int = 40, n_shift: int = 199, seed: int = 0,
                     synthetic_days: int | None = None) -> pd.Series:
    """p-values of the circular-shift test for Markov gates independent of returns; they should look uniform.
    Returns: dev-period TRI (2002-2007), or synthetic_days of GARCH-t returns fitted to the dev period."""
    if synthetic_days:
        params = json.loads((settings.data_dir / "results" / "synthetic_dgp_params.json").read_text())["garch_t"]
        tri = 100 * (1 + synthetic.simulate_garch_t(synthetic_days + 1, **params, seed=seed)).cumprod()
        idx = tri.index[1:]
    else:
        tri = pd.read_parquet(settings.data_dir / "processed" / "nifty50_tri.parquet").set_index("date")["tri"]
        tri = tri.loc["2001-12-01":DEV_END]
        idx = tri.loc["2002-01-01":].index
    rng = np.random.default_rng(seed)
    pvals = []
    for _ in range(n_gates):
        g = np.zeros(len(idx))
        for t in range(1, len(idx)):
            stay = 0.99 if g[t - 1] == 0 else 0.95
            g[t] = g[t - 1] if rng.random() < stay else 1 - g[t - 1]

        def run(gate: np.ndarray) -> float:
            r = tri_returns(tri, pd.Series(0.0, tri.index), pd.Series(gate, idx).reindex(tri.index), 1,
                            *TRI_TIERS["headline"]).loc[idx].to_numpy()
            return stats.sharpe(r, np.zeros(len(r)))

        pvals.append(stats.circular_shift_test(run, g, n_shift, seed=int(rng.integers(1 << 31)))["p_value"])
    return pd.Series(pvals, name="p_value")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["straddle", "null"])
    parser.add_argument("dates", nargs="*", type=pd.Timestamp, help="days inside the cycles to check")
    parser.add_argument("--gates", type=int, default=40, help="null: number of uninformative gates")
    parser.add_argument("--synthetic-days", type=int, default=None, help="null: GARCH-t returns instead of dev TRI")
    args = parser.parse_args()
    if args.what == "straddle":
        panel = pd.read_parquet(settings.data_dir / "processed" / "nifty_fo.parquet")
        expiries, days = straddle.monthly_expiries(panel), pd.DatetimeIndex(sorted(panel["date"].unique()))
        for day in args.dates:
            expiry = expiries[expiries >= day][0].date()
            entry = days[days > expiries[expiries < day][-1]][0].date()
            for spread in (0.0, 0.01):
                hand, legs = straddle_by_hand(entry, expiry, spread)
                engine = straddle_by_engine(panel, entry, expiry, spread)
                print(f"{entry} to {expiry} half-spread {spread:.2%}: by hand {hand:+.6%}, engine {engine:+.6%}, "
                      f"diff {engine - hand:+.2e} | {legs}")
    else:
        p = null_calibration(args.gates, synthetic_days=args.synthetic_days)
        print(f"{len(p)} uninformative gates: mean p {p.mean():.3f}, share p<0.05 {np.mean(p < 0.05):.3f}, "
              f"share p<0.10 {np.mean(p < 0.10):.3f}")


if __name__ == "__main__":
    main()
