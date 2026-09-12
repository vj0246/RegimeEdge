import numpy as np
import pandas as pd

from osr.data import validate as v

D = pd.Timestamp


def panel_rows(rows):
    cols = ["date", "instrument", "expiry", "strike", "opt_type", "close", "settle", "volume"]
    return pd.DataFrame(rows, columns=cols)


def test_calendar_mismatches_within_fo_range():
    fo = pd.Series([D("2020-01-01"), D("2020-01-02"), D("2020-01-03")])
    ix = pd.Series([D("2019-12-31"), D("2020-01-01"), D("2020-01-03"), D("2020-01-06")])
    assert v.calendar_mismatches(fo, ix) == ([D("2020-01-02")], [])


def test_expiry_settlement_gap_flags_mismatch():
    panel = panel_rows([
        (D("2020-01-30"), "FUT", D("2020-01-30"), np.nan, None, 100.0, 100.00, 10),
        (D("2020-01-30"), "FUT", D("2020-02-27"), np.nan, None, 101.0, 101.00, 10),
        (D("2020-02-27"), "FUT", D("2020-02-27"), np.nan, None, 99.0, 99.50, 10),
    ])
    close = pd.Series([100.02, 99.0], index=[D("2020-01-30"), D("2020-02-27")])
    gaps = v.expiry_settlement_gaps(panel, close)
    assert len(gaps) == 2
    assert list(gaps["gap"] > v.SETTLE_TOL) == [False, True]


def test_tri_ratio_detects_fall_and_band():
    idx = pd.bdate_range("2001-01-01", "2001-12-31")
    price = pd.Series(1000.0, index=idx)
    tri = pd.Series(np.linspace(1000, 1015, len(idx)), index=idx)  # 1.5% a year
    falls, off = v.tri_ratio_problems(price, tri)
    assert falls.empty and off.empty
    tri.iloc[100] = tri.iloc[99] * 0.99
    falls, _ = v.tri_ratio_problems(price, tri)
    assert len(falls) == 1


def test_parity_deviation_zero_at_exact_parity():
    d, e = D("2020-01-10"), D("2020-01-30")
    panel = panel_rows([
        (d, "FUT", e, np.nan, None, 1010.0, 1010.0, 5),
        (d, "OPT", e, 1000.0, "CE", 30.0, 30.0, 5),
        (d, "OPT", e, 1000.0, "PE", 20.0, 20.0, 5),
        (d, "OPT", e, 1100.0, "CE", 1.0, 1.0, 5),
        (d, "OPT", e, 1100.0, "PE", 95.0, 95.0, 0),  # untraded, ignored
    ])
    dev = v.parity_deviation(panel)
    assert list(dev.index) == [d] and dev.iloc[0] == 0.0


def test_expiry_calendar_problems():
    trading = pd.DatetimeIndex(["2020-01-30", "2020-02-27", "2020-03-25", "2020-03-26"])
    ok = pd.DatetimeIndex(["2020-01-30", "2020-02-27", "2020-03-26"])
    assert v.expiry_calendar_problems(ok, trading, D("2020-01-01"), D("2020-03-31")) == []
    two = pd.DatetimeIndex(["2020-01-30", "2020-02-27", "2020-03-25", "2020-03-26"])
    assert v.expiry_calendar_problems(two, trading, D("2020-01-01"), D("2020-03-31")) == ["2020-03: 2 expiries"]
    holiday = pd.DatetimeIndex(["2020-01-30", "2020-02-28", "2020-03-26"])
    assert v.expiry_calendar_problems(holiday, trading, D("2020-01-01"), D("2020-03-31")) == ["2020-02-28: not a trading day"]


def test_tbill_conflicts():
    raw = pd.DataFrame({"date": [D("2011-04-06"), D("2011-04-06"), D("2011-04-13"), D("2011-04-13"), D("2011-04-20")],
                        "yield_pct": [7.1443, 7.1448, 7.18, 7.25, 7.3]})
    n_multi, conflicts = v.tbill_conflicts(raw)
    assert n_multi == 2 and list(conflicts.index) == [D("2011-04-13")]


def test_long_gaps():
    dates = pd.Series([D("2020-01-01"), D("2020-01-02"), D("2020-01-10")])  # 5 weekdays missing
    gaps = v.long_gaps(dates)
    assert len(gaps) == 1 and gaps.loc[0, "missing_weekdays"] == 5
