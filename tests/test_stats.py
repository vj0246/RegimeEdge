import json
import math

import numpy as np
import pandas as pd
import pytest

from osr.engine import ledger, stats

T = 3000


def test_mppm_constant_return_is_annualised_log_return():
    r, rf = np.full(100, 0.001), np.zeros(100)
    assert stats.mppm(r, rf) == pytest.approx(252 * math.log(1.001))


def test_mppm_penalises_variance_at_equal_mean():
    rng = np.random.default_rng(0)
    z = rng.standard_normal(T)
    calm, wild, rf = 0.0005 + 0.005 * z, 0.0005 + 0.02 * z, np.zeros(T)
    assert stats.mppm(calm, rf) > stats.mppm(wild, rf)


def test_drawdown_and_cvar():
    assert stats.max_drawdown(np.array([0.1, -0.5, 0.2])) == pytest.approx(-0.5)
    assert stats.cvar(np.arange(-10, 10) / 100, level=0.9) == pytest.approx(-0.095)


def test_sharpe_difference_se_matches_iid_formula():
    rng = np.random.default_rng(1)
    x1, x2 = 0.0004 + 0.01 * rng.standard_normal(T), 0.0002 + 0.01 * rng.standard_normal(T)
    _, se = stats.sharpe_diff_and_se(x1, x2)
    s1, s2 = x1.mean() / x1.std(), x2.mean() / x2.std()
    assert se == pytest.approx(math.sqrt((2 + s1**2 / 2 + s2**2 / 2) / T), rel=0.15)


def test_sharpe_difference_test_power_and_size():
    rng = np.random.default_rng(2)
    base, rf = 0.01 * rng.standard_normal(T), np.zeros(T)
    strong = stats.sharpe_difference_test(base + 0.002, base + 0.003 * rng.standard_normal(T), rf, n_boot=500)
    assert strong["diff"] > 0 and strong["p_value"] < 0.01
    null = stats.sharpe_difference_test(base, base + 0.003 * rng.standard_normal(T), rf, n_boot=500)
    assert null["p_value"] > 0.05 and null["ci_low"] < 0 < null["ci_high"]


def test_paired_difference_test_detects_mean_shift():
    rng = np.random.default_rng(3)
    base, rf = 0.01 * rng.standard_normal(T), np.zeros(T)
    out = stats.paired_difference_test(base + 0.001, base, rf, stats.mppm, n_boot=500)
    assert out["diff"] == pytest.approx(stats.mppm(base + 0.001, rf) - stats.mppm(base, rf))
    assert out["p_value"] < 0.01


def test_circular_shift_rewards_timing_only():
    rng = np.random.default_rng(4)
    bad_days = (rng.random(T) < 0.1).astype(float)
    returns = np.where(bad_days == 1, -0.03, 0.002)
    run = lambda g: float(np.mean((1 - g) * returns))  # noqa: E731
    assert stats.circular_shift_test(run, bad_days, n=199)["p_value"] < 0.01
    assert stats.circular_shift_test(run, (rng.random(T) < 0.1).astype(float), n=199)["p_value"] > 0.05


def test_expected_max_sharpe_and_psr():
    assert stats.expected_max_sharpe(1, 0.01) == 0
    assert stats.expected_max_sharpe(10, 0.01) < stats.expected_max_sharpe(100, 0.01)
    x = np.random.default_rng(5).standard_normal(T) * 0.01 + 0.0005
    sr = x.mean() / x.std(ddof=1)
    assert stats.probabilistic_sharpe(x, 0.0) == pytest.approx(0.5 * (1 + math.erf(sr * math.sqrt(T - 1) / math.sqrt(2))), abs=0.02)


def test_effective_trials_finds_two_groups():
    rng = np.random.default_rng(6)
    a, b = rng.standard_normal((2, T))
    cols = {f"a{i}": a + 0.1 * rng.standard_normal(T) for i in range(3)}
    cols |= {f"b{i}": b + 0.1 * rng.standard_normal(T) for i in range(3)}
    k, labels, _ = stats.effective_trials(pd.DataFrame(cols))
    assert k == 2 and len(set(labels[:3])) == 1 and len(set(labels[3:])) == 1


def test_pbo_noise_versus_skill():
    rng = np.random.default_rng(7)
    noise, rf = 0.01 * rng.standard_normal((2000, 8)), np.zeros(2000)
    assert 0.2 < stats.pbo_cscv(noise, rf) < 0.8
    skilled = noise.copy()
    skilled[:, 0] += 0.003
    assert stats.pbo_cscv(skilled, rf) < 0.05
    assert stats.pbo_cscv(skilled, rf, metric="mppm") < 0.05


def test_ledger_appends_one_canonical_row(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger.append({"b": 1, "a": 2}, "abc", "r.parquet", {"sharpe": 0.5}, path=path)
    ledger.append({"a": 2, "b": 1}, "abc", "r.parquet", {"sharpe": 0.5}, path=path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["config_sha256"] == rows[1]["config_sha256"]
