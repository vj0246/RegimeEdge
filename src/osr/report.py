"""Confirmatory tests and selection-bias statistics (decisions.md sections 10 and 11)."""

import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from osr.engine import stats
from osr.engine.costs import TRI_TIERS
from osr.strategies import straddle
from osr.strategies.tri import tri_returns

COMPARATORS = {"S": ("ungated", "RV", "IV"), "T": ("ungated", "RV")}
DETECTORS = ("HMM-2", "JM")


def holm(p: pd.Series) -> pd.Series:
    order = p.sort_values()
    adjusted = np.maximum.accumulate([(len(order) - i) * v for i, v in enumerate(order)])
    return pd.Series(np.minimum(adjusted, 1.0), index=order.index).reindex(p.index)


def confirmatory(track: str, returns: pd.DataFrame, rf: np.ndarray, rerun: Callable[[np.ndarray], float],
                 gates: dict[str, np.ndarray], n_boot: int = 10_000, n_shift: int = 999) -> pd.DataFrame:
    """Section 10 tests for HMM-2 and JM, with Holm adjustment across the track's tests."""
    years = len(returns) / stats.PERIODS
    rows = []
    for d in DETECTORS:
        for c in COMPARATORS[track]:
            r1, r2 = returns[d].to_numpy(), returns[c].to_numpy()
            res = (stats.sharpe_difference_test(r1, r2, rf, n_boot) if track == "T"
                   else stats.paired_difference_test(r1, r2, rf, stats.mppm, n_boot))
            rho = np.corrcoef(r1, r2)[0, 1]
            rows.append({"detector": d, "comparator": c, **res, "mde_sharpe": 2.8 * math.sqrt(2 * (1 - rho) / years)})
        shift = stats.circular_shift_test(rerun, gates[d], n_shift)
        rows.append({"detector": d, "comparator": "circular shift", "diff": shift["observed"] - shift["null_mean"],
                     "p_value": shift["p_value"]})
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out["p_value"]).to_numpy()
    return out


def selection(track: str, returns: pd.DataFrame, rf: np.ndarray) -> pd.DataFrame:
    """Section 11: DSR with clustered effective trials, and PBO by CSCV."""
    excess = pd.DataFrame(returns.to_numpy() - rf[:, None], columns=returns.columns)
    k, _, var_sr = stats.effective_trials(excess)
    sr0 = stats.expected_max_sharpe(k, var_sr)
    pbo = stats.pbo_cscv(returns.to_numpy(), rf, metric="sharpe" if track == "T" else "mppm")
    return pd.DataFrame([{"detector": d, "dsr": stats.probabilistic_sharpe(excess[d].to_numpy(), sr0),
                          "n_effective": k, "n_raw": returns.shape[1], "sr0_annual": sr0 * math.sqrt(stats.PERIODS),
                          "pbo": pbo} for d in DETECTORS])


def run(out: Path, inp, gates: dict[str, pd.Series], t_ret: pd.DataFrame, s_ret: pd.DataFrame,
        plan: straddle.Plan, rf_s: pd.Series, lag: int, tier: str, half_spread: float) -> None:
    """Rotated gates are applied inside the evaluation window only; outside it the strategy is invested."""
    tri = inp.tri.loc[: t_ret.index[-1]]
    rf_tri = inp.rf.reindex(tri.index).fillna(0.0)

    def rerun_t(g: np.ndarray) -> float:
        gate = pd.Series(g, index=t_ret.index).reindex(tri.index)
        r = tri_returns(tri, rf_tri, gate, lag, *TRI_TIERS[tier]).loc[t_ret.index].to_numpy()
        return stats.sharpe(r, rf_tri.loc[t_ret.index].to_numpy())

    def rerun_s(g: np.ndarray) -> float:
        full = pd.Series(g, index=s_ret.index).reindex(plan.dates).to_numpy()
        r = straddle.simulate(plan, full, lag, half_spread).loc[s_ret.index].to_numpy()
        return stats.mppm(r, rf_s.loc[s_ret.index].to_numpy())

    for track, ret, rerun, rf in (("T", t_ret, rerun_t, inp.rf), ("S", s_ret, rerun_s, rf_s)):
        f = rf.reindex(ret.index).fillna(0.0).to_numpy()
        conf = confirmatory(track, ret, f, rerun, {d: gates[d].reindex(ret.index).fillna(0.0).to_numpy()
                                                   for d in DETECTORS})
        sel = selection(track, ret, f)
        conf.to_csv(out / f"confirmatory_track{track}.csv", index=False)
        sel.to_csv(out / f"selection_track{track}.csv", index=False)
        print(f"\nConfirmatory, Track {track}\n{conf.round(4).to_string(index=False)}")
        print(f"\nSelection, Track {track}\n{sel.round(4).to_string(index=False)}")
