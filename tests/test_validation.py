import numpy as np
import pandas as pd
import pytest

from osr import synthetic
from osr.detectors.base import gate_path, majority_filter
from osr.detectors.features import detector_inputs
from osr.detectors.threshold import PercentileGate
from osr.validation import detection_stats, percentile_sweep, refit_stability


def test_majority_filter_is_causal_and_needs_a_full_window():
    raw = pd.Series([np.nan, 0, 1, 1, 0, 0, 1, 1, 1, 0], dtype=float)
    out = majority_filter(raw, 3)
    assert out.isna().tolist() == [True] * 3 + [False] * 7
    assert out.dropna().tolist() == [1, 1, 0, 0, 1, 1, 1]
    changed = raw.copy()
    changed.iloc[8:] = 0
    assert majority_filter(changed, 3).iloc[:8].equals(out.iloc[:8])


def test_detection_stats_delay_miss_and_false_alarms():
    s = np.array([0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0], dtype=float)
    g = np.array([0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 0, 1], dtype=float)
    out = detection_stats(g, s)
    assert out["episodes"] == 2 and out["miss_rate"] == 0
    assert out["delay_median"] == 1  # both episodes flagged one day in
    assert out["false_alarms_per_year"] == pytest.approx(1 / (7 / 252))  # only the rise at 11 is in calm
    assert out["flat_share"] == 0.5


def test_detection_stats_without_states_ignores_warm_up():
    out = detection_stats(np.array([np.nan, 0, 1, 1, 0]), None)
    assert out["flat_share"] == 0.5 and out["switches_per_year"] == pytest.approx(2 / (4 / 252))


def test_hsmm_durations_and_state_volatility_match_targets():
    r, s = synthetic.simulate_hsmm_t(200_000, [0.0, 0.0], [0.01, 0.02], [100.0, 30.0], seed=0)
    v = s.to_numpy()
    starts = np.r_[0, np.flatnonzero(np.diff(v)) + 1]
    lengths, kinds = np.diff(np.r_[starts, len(v)]), v[starts]
    for k, target in ((0, 100.0), (1, 30.0)):
        assert lengths[kinds == k][1:-1].mean() == pytest.approx(target, rel=0.1)
    assert r[s == 1].std() == pytest.approx(0.02, rel=0.05)


def test_garch_matches_unconditional_variance():
    r = synthetic.simulate_garch_t(100_000, mu=0.05, omega=0.05, alpha=0.06, beta=0.9, nu=8.0, seed=1)
    assert r.var() == pytest.approx(0.05 / (1 - 0.96) / 1e4, rel=0.15)


def test_percentile_sweep_matches_gate_path():
    r, _ = synthetic.simulate_hmm(2600, [0.0005, -0.001], [0.008, 0.025], [[0.99, 0.01], [0.03, 0.97]], seed=3)
    x = detector_inputs(r)
    refits = list(x.index[999::100])
    sweep = percentile_sweep(lambda: PercentileGate("rv"), x, refits, [80.0], window=1500, min_history=1000)
    pd.testing.assert_series_equal(sweep[80.0], gate_path(lambda: PercentileGate("rv"), x, refits, 1500, 1000))


def flag_detector(invert_alternate_fits: bool):
    fits = {"n": 0}

    class Flag:
        def fit(self, x):
            fits["n"] += 1
            self.invert = invert_alternate_fits and fits["n"] % 2 == 0

        def insample_stressed(self, x):
            f = x["flag"].to_numpy()
            return 1 - f if self.invert else f

    return Flag


def test_refit_stability_separates_label_flips_from_partition_changes():
    idx = pd.bdate_range("2000-01-03", periods=400)
    x = pd.DataFrame({"flag": (np.arange(400) // 37) % 2}, index=idx)
    refits = list(idx[199::50])
    same = refit_stability(flag_detector(False), x, refits, window=200, min_history=200)
    assert len(same) == 4 and (same["overlap"] == 150).all()
    assert (same["ari"] == 1).all() and (same["flip_rate"] == 0).all()
    flipped = refit_stability(flag_detector(True), x, refits, window=200, min_history=200)
    assert (flipped["ari"] == 1).all() and (flipped["flip_rate"] == 1).all()
