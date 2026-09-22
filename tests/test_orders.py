"""Order guards against a fake Kite client. No test reads the real .env or sends anything."""

import datetime as dt
import json

import pandas as pd
import pytest

from osr.live import orders
from osr.live.instruments import nifty_instruments
from osr.live.settings import KiteSettings

E1 = dt.date(2026, 9, 29)
OPEN_TIME = dt.datetime(2026, 9, 15, 10, 0, tzinfo=orders.IST)  # a Tuesday


class FakeKite:
    def __init__(self, bid=99.97, ask=100.03, margin_need=100_000.0, margin_have=500_000.0):
        self.bid, self.ask, self.need, self.have = bid, ask, margin_need, margin_have
        self.placed = []

    def instruments(self, exchange):
        rows = [dict(tradingsymbol="NIFTY26SEPFUT", name="NIFTY", instrument_type="FUT", expiry=E1, strike=0.0,
                     lot_size=65)]
        rows += [dict(tradingsymbol=f"NIFTY26SEP{k}{t}", name="NIFTY", instrument_type=t, expiry=E1, strike=float(k),
                      lot_size=65) for k in (24400, 24500, 24600) for t in ("CE", "PE")]
        return rows

    def quote(self, keys):
        return {k: {"last_price": 24480.0 if k.endswith("FUT") else 100.0,
                    "depth": {"buy": [{"price": self.bid, "quantity": 65}], "sell": [{"price": self.ask, "quantity": 65}]}}
                for k in keys}

    def basket_order_margins(self, params):
        return {"final": {"total": self.need}}

    def margins(self, segment):
        return {"net": self.have}

    def place_order(self, **kw):
        self.placed.append(kw)
        return f"order{len(self.placed)}"


@pytest.fixture
def live_settings(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "k")
    monkeypatch.setenv("KITE_API_SECRET", "s")
    monkeypatch.setenv("KITE_LIVE_TRADING", "true")
    return KiteSettings(_env_file=None)


def legs_for(kite):
    inst = nifty_instruments(kite)
    expiry, strike = orders.resolve(kite, inst, "near", "ATM", pd.Timestamp("2026-09-15"))
    return orders.straddle_legs(kite, inst, expiry, strike, 1, "SELL")


def test_to_tick_rounds_towards_a_fill():
    assert orders.to_tick(120.52, "SELL") == 120.5 and orders.to_tick(120.52, "BUY") == 120.55
    assert orders.to_tick(120.5, "SELL") == 120.5 == orders.to_tick(120.5, "BUY")


def test_atm_legs_priced_at_the_bid():
    legs = legs_for(FakeKite())
    assert [leg.tradingsymbol for leg in legs] == ["NIFTY26SEP24500CE", "NIFTY26SEP24500PE"]
    assert all(leg.price == 99.95 and leg.quantity == 65 and leg.transaction_type == "SELL" for leg in legs)


def test_wide_quote_is_refused():
    with pytest.raises(ValueError):
        legs_for(FakeKite(bid=50.0, ask=150.0))


def test_all_guards_pass_sends_two_limit_orders(live_settings, tmp_path):
    kite = FakeKite()
    legs = legs_for(kite)
    text = " ; ".join(f"SELL {leg.tradingsymbol} x65 @ 99.95" for leg in legs)
    ids = orders.execute(kite, legs, live_settings, 1, True, confirm=lambda _: text, now=OPEN_TIME,
                         kill_switch=tmp_path / "STOP", log_path=tmp_path / "log.jsonl")
    assert ids == ["order1", "order2"]
    assert {p["order_type"] for p in kite.placed} == {"LIMIT"} and {p["product"] for p in kite.placed} == {"NRML"}
    assert [json.loads(line)["status"] for line in (tmp_path / "log.jsonl").read_text().splitlines()] == ["sent", "sent"]


@pytest.mark.parametrize("case", ["no_live_flag", "env_off", "kill_switch", "too_many_lots", "after_hours",
                                  "margin_short", "not_confirmed"])
def test_each_guard_blocks(case, live_settings, tmp_path, monkeypatch):
    kite = FakeKite(margin_need=900_000.0) if case == "margin_short" else FakeKite()
    legs = legs_for(kite)
    s = live_settings
    if case == "env_off":
        monkeypatch.setenv("KITE_LIVE_TRADING", "false")
        s = KiteSettings(_env_file=None)
    if case == "kill_switch":
        (tmp_path / "STOP").touch()
    ids = orders.execute(kite, legs, s, 2 if case == "too_many_lots" else 1, case != "no_live_flag",
                         confirm=lambda _: "yes" if case == "not_confirmed" else " ; ".join(
                             f"SELL {leg.tradingsymbol} x65 @ 99.95" for leg in legs),
                         now=OPEN_TIME.replace(hour=16) if case == "after_hours" else OPEN_TIME,
                         kill_switch=tmp_path / "STOP", log_path=tmp_path / "log.jsonl")
    assert ids == [] and kite.placed == []
    assert json.loads((tmp_path / "log.jsonl").read_text().splitlines()[-1])["status"] in {"dry_run", "not_confirmed"}
