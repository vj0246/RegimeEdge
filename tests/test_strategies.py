import numpy as np
import pandas as pd
import pytest

from osr.engine import costs
from osr.strategies import straddle
from osr.strategies.black76 import straddle_iv, straddle_value
from osr.strategies.tri import tri_returns

D = pd.Timestamp
E0, E1 = D("2020-01-30"), D("2020-02-27")
DATES = [E0, D("2020-01-31"), D("2020-02-03"), D("2020-02-04"), E1]


def test_cost_constants_match_decisions_md():
    assert round(costs.OPT_SELL * 100, 5) == 0.19204
    assert round(costs.OPT_BUY * 100, 5) == 0.04504
    assert [round(c * 100, 4) for c in costs.TRI_TIERS["headline"]] == [0.0143, 0.0623]
    assert [round(c * 100, 4) for c in costs.TRI_TIERS["delivery"]] == [0.1287, 0.1137]


def test_tri_gate_timing_and_costs():
    idx = pd.bdate_range("2020-01-01", periods=6)
    tri = pd.Series([100, 101, 102, 103, 104, 105], index=idx, dtype=float)
    rf = pd.Series(0.001, index=idx)
    gate = pd.Series([0, 1, 1, 0, 0, 0], index=idx, dtype=float)  # flat signal at close of day 1
    r = tri_returns(tri, rf, gate, lag=1, buy=0.01, sell=0.02)
    tri_r = tri.pct_change()
    # sold at close of day 2 (cost 2%), cash over days 3 and 4, bought back at close of day 4 (cost 1%)
    assert r.iloc[1] == pytest.approx(tri_r.iloc[1])
    assert r.iloc[2] == pytest.approx(tri_r.iloc[2] - 0.02)
    assert r.iloc[3] == pytest.approx(0.001)
    assert r.iloc[4] == pytest.approx(0.001 - 0.01)
    assert r.iloc[5] == pytest.approx(tri_r.iloc[5])
    bh = tri_returns(tri, rf)
    assert np.prod(1 + bh.dropna()) == pytest.approx(105 / 100)


def toy_panel() -> pd.DataFrame:
    fut = [(E0, E0, 100.0), (DATES[1], E1, 101.0), (DATES[2], E1, 102.0), (DATES[3], E1, 99.0), (E1, E1, 105.0)]
    rows = [{"date": d, "instrument": "FUT", "expiry": e, "strike": np.nan, "opt_type": None,
             "close": s, "settle": s, "volume": 10} for d, e, s in fut]
    opt = [  # date, strike, type, close, settle, volume
        (DATES[1], 100, "CE", 3.0, 3.0, 10), (DATES[1], 100, "PE", 2.0, 2.0, 10),
        (DATES[1], 102, "CE", 2.0, 2.0, 5), (DATES[1], 102, "PE", 3.1, 3.1, 0),  # untraded put: strike unusable
        (DATES[2], 100, "CE", 3.5, 3.5, 10), (DATES[2], 100, "PE", 1.5, 1.5, 10),
        (DATES[3], 100, "CE", 2.2, 2.0, 0), (DATES[3], 100, "PE", 2.4, 2.5, 5),
    ]
    rows += [{"date": d, "instrument": "OPT", "expiry": E1, "strike": float(k), "opt_type": t,
              "close": c, "settle": s, "volume": v} for d, k, t, c, s, v in opt]
    return pd.DataFrame(rows)


@pytest.fixture
def plan():
    return straddle.build_plan(toy_panel(), pd.Series(0.0, index=pd.DatetimeIndex(DATES)))


def test_plan_picks_nearest_strike_with_both_legs_traded(plan):
    ok = plan.cycles[plan.cycles["status"] == "ok"]
    assert len(ok) == 1 and ok["strike"].iloc[0] == 100 and ok["entry"].iloc[0] == DATES[1]
    assert list(plan.entry) == [False, True, False, False, False]
    assert plan.payoff[0] == 5.0 and plan.premium[0] == 5.0


def test_ungated_cycle_reconciles_by_hand(plan):
    r = straddle.simulate(plan, None, half_spread=0.0)
    units = 1 / 101
    cash = 1 + units * 5.0 * (1 - costs.OPT_SELL)
    v = [1.0, cash - units * 5.0, cash - units * 5.0, cash - units * 4.5, cash - units * 5.0]
    assert np.allclose((1 + r).cumprod(), v)


def test_gate_exit_uses_close_if_traded_else_settlement(plan):
    r = straddle.simulate(plan, np.array([0, 0, 1, 0, 0]), lag=1, half_spread=0.0)
    units = 1 / 101
    cash = 1 + units * 5.0 * (1 - costs.OPT_SELL)
    after_exit = cash - units * (2.0 + 2.4) * (1 + costs.OPT_BUY)  # call untraded: settlement; put: close
    assert np.allclose((1 + r).cumprod(), [1.0, cash - units * 5.0, cash - units * 5.0, after_exit, after_exit])


def test_gate_blocks_entry(plan):
    r = straddle.simulate(plan, np.array([1, 0, 0, 0, 0]), lag=1)
    assert np.allclose(r, 0.0)


def test_atm_iv_prefers_traded_closes_then_settlements():
    auctions = pd.DataFrame({"date": [D("2020-01-01")], "yield_pct": [6.0]})
    iv = straddle.atm_iv(toy_panel(), auctions)
    assert list(iv.index) == [DATES[1], DATES[2], DATES[3]]  # E0 has no E1 options; E1 has no later expiry
    assert iv[DATES[1]] == pytest.approx(straddle_iv(5.0, 101.0, 100.0, 27 / 365, 0.06))
    assert iv[DATES[3]] == pytest.approx(straddle_iv(4.5, 99.0, 100.0, 23 / 365, 0.06))  # call untraded


def test_black76_straddle_iv_round_trip():
    price = straddle_value(22000.0, 22100.0, 30 / 365, 0.065, 0.14)
    assert straddle_iv(price, 22000.0, 22100.0, 30 / 365, 0.065) == pytest.approx(0.14, abs=1e-8)
    assert np.isnan(straddle_iv(1.0, 22000.0, 22100.0, 30 / 365, 0.065))  # below intrinsic value
