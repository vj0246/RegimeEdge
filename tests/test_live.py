"""Kite code against a fake client. No test reads the real .env (every KiteSettings uses _env_file=None)."""

import datetime as dt

import pandas as pd
import pytest
from pydantic import ValidationError

from osr.live import recorder, session
from osr.live.instruments import monthly_expiries, nifty_instruments, strikes_around
from osr.live.settings import KiteSettings

E1, E2 = dt.date(2026, 9, 29), dt.date(2026, 10, 27)


class FakeKite:
    def __init__(self):
        self.quote_calls = []

    def instruments(self, exchange):
        rows = [dict(tradingsymbol=f"NIFTY26{m}FUT", name="NIFTY", instrument_type="FUT", expiry=e, strike=0.0,
                     lot_size=65) for m, e in (("SEP", E1), ("OCT", E2))]
        rows += [dict(tradingsymbol=f"NIFTY26{m}{k}{t}", name="NIFTY", instrument_type=t, expiry=e, strike=float(k),
                      lot_size=65) for m, e in (("SEP", E1), ("OCT", E2)) for k in range(24000, 25001, 100)
                 for t in ("CE", "PE")]
        rows.append(dict(tradingsymbol="BANKNIFTY26SEPFUT", name="BANKNIFTY", instrument_type="FUT", expiry=E1,
                         strike=0.0, lot_size=30))
        return rows

    def quote(self, instruments):
        self.quote_calls.append(list(instruments))
        out = {}
        for key in instruments:
            px = 24400.0 if key == recorder.INDEX else 24480.0 if key.endswith("FUT") else 100.0
            depth = {} if key == recorder.INDEX else {"buy": [{"price": px - 1, "quantity": 65}] * 5,
                                                      "sell": [{"price": px + 1, "quantity": 65}] * 5}
            out[key] = {"last_price": px, "volume": 10, "oi": 5, "timestamp": "2026-09-14 15:20:00", "depth": depth}
        return out


def test_instruments_keep_nifty_and_find_monthly_expiries():
    inst = nifty_instruments(FakeKite())
    assert set(inst["name"]) == {"NIFTY"}
    assert monthly_expiries(inst) == [pd.Timestamp(E1), pd.Timestamp(E2)]


def test_strikes_around_the_forward():
    inst = nifty_instruments(FakeKite())
    legs = strikes_around(inst, pd.Timestamp(E1), 24480.0, 2)  # nearest strike 24500
    assert sorted(legs["strike"].unique()) == [24300.0, 24400.0, 24500.0, 24600.0, 24700.0]
    assert len(legs) == 10


def test_snapshot_rows_depth_and_half_spread():
    kite = FakeKite()
    df = recorder.snapshot(kite, n_strikes=2, pause_s=0)
    assert len(df) == 1 + 2 + 2 * 10  # index, two futures, two chains
    assert len(kite.quote_calls) == 2 and len(kite.quote_calls[1]) == 20
    opts = df[df["instrument_type"].isin(["CE", "PE"])]
    assert opts["half_spread_pct"].tolist() == pytest.approx([0.01] * 20)  # bid 99, ask 101
    assert {"bid5", "ask5_qty"} <= set(df.columns)
    assert df.loc[df["symbol"] == recorder.INDEX, "half_spread_pct"].isna().all()


def test_save_token_replaces_only_its_line(tmp_path):
    env = tmp_path / ".env"
    env.write_text("KITE_API_KEY=k\nKITE_ACCESS_TOKEN=old\nKITE_API_SECRET=s\n", encoding="utf-8")
    session.save_token("new", env)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines.count("KITE_ACCESS_TOKEN=new") == 1 and "KITE_ACCESS_TOKEN=old" not in lines
    assert {"KITE_API_KEY=k", "KITE_API_SECRET=s"} <= set(lines)


def test_settings_require_key_and_secret(monkeypatch):
    for name in ("KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN", "KITE_LIVE_TRADING"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValidationError):
        KiteSettings(_env_file=None)
    monkeypatch.setenv("KITE_API_KEY", "key-SENTINEL-1")
    monkeypatch.setenv("KITE_API_SECRET", "secret-SENTINEL-2")
    s = KiteSettings(_env_file=None)
    assert s.live_trading is False and s.max_lots == 1
    assert "SENTINEL" not in repr(s) and "SENTINEL" not in str(s)  # secrets are masked
    assert s.api_key.get_secret_value() == "key-SENTINEL-1"


def test_client_refuses_without_a_token(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "k")
    monkeypatch.setenv("KITE_API_SECRET", "s")
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        session.client(KiteSettings(_env_file=None))
