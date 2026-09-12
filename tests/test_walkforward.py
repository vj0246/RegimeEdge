import numpy as np
import pandas as pd
import pytest

from osr import lock
from osr.report import holm
from osr.walkforward import select_jm


def test_holm_step_down():
    adjusted = holm(pd.Series({"a": 0.01, "b": 0.04, "c": 0.03}))
    assert adjusted.to_dict() == pytest.approx({"a": 0.03, "b": 0.06, "c": 0.06})


def test_select_jm_follows_trailing_sharpe_and_waits_for_history():
    idx = pd.bdate_range("2000-01-03", periods=1200)
    rng = np.random.default_rng(0)
    crash = (idx >= "2001-06-01") & (idx < "2001-09-01")
    tri = pd.Series(100 * np.cumprod(1 + np.where(crash, -0.01, 0.0008) + 0.002 * rng.standard_normal(len(idx))), idx)
    always_in = pd.Series(0.0, idx)
    avoids_crash = pd.Series(np.where(crash, 1.0, 0.0), idx)  # perfect foresight, flat through the crash
    selection = list(idx[::21])
    gate, chosen = select_jm({5.0: always_in, 50.0: avoids_crash}, tri, pd.Series(0.0, idx), selection,
                             validation=pd.DateOffset(years=8), min_days=500)
    first = chosen.first_valid_index()
    assert first >= idx[500]
    assert (chosen.dropna() == 50.0).all()
    assert gate.loc[first:].equals(avoids_crash.loc[first:].rename("gate"))


def test_lock_detects_changes(tmp_path):
    decisions, manifest, lock_file = tmp_path / "decisions.md", tmp_path / "manifest.json", tmp_path / "prereg.lock"
    decisions.write_bytes(b"spec\r\n")
    manifest.write_bytes(b"{}")
    lock.create(lock_file, decisions=decisions, manifest=manifest)
    decisions.write_bytes(b"spec\n")  # line-ending change only: still verifies
    lock.verify(lock_file, check_git=False, decisions=decisions, manifest=manifest)
    decisions.write_bytes(b"spec, amended\n")
    with pytest.raises(RuntimeError):
        lock.verify(lock_file, check_git=False, decisions=decisions, manifest=manifest)
