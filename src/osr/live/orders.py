"""Guarded Kite orders for the NIFTY straddle. A dry run unless every guard passes.

  python -m osr.live.orders straddle --side SELL --expiry near --strike ATM --lots 1 [--live]

A real order needs all of: --live, KITE_LIVE_TRADING=true in .env, no STOP_TRADING file in the project root,
lots <= KITE_MAX_LOTS, NSE F&O hours, enough margin, and the exact order text typed back. Orders are LIMIT only,
priced at the touch from a fresh quote; legs quoted wider than MAX_HALF_SPREAD are refused. Every attempt is
appended to data/live/orders.jsonl. Since 1 Apr 2026 Kite takes API orders only from a static IP registered in
the developer console.
"""

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from kiteconnect import KiteConnect

from osr.config import settings
from osr.live.instruments import monthly_expiries, nifty_instruments
from osr.live.session import client
from osr.live.settings import KiteSettings

IST = ZoneInfo("Asia/Kolkata")
KILL_SWITCH = Path("STOP_TRADING")
MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)
TICK = 0.05
MAX_HALF_SPREAD = 0.05  # of mid


@dataclass(frozen=True)
class Leg:
    tradingsymbol: str
    transaction_type: str  # SELL or BUY
    quantity: int
    price: float


def to_tick(price: float, side: str) -> float:
    """Round a limit price to the tick towards a fill: sells down, buys up."""
    ticks = price / TICK
    return round((math.floor(ticks + 1e-9) if side == "SELL" else math.ceil(ticks - 1e-9)) * TICK, 2)


def resolve(kite, inst: pd.DataFrame, expiry: str, strike: str, today: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    """expiry 'near' or 'next' monthly; strike 'ATM' (nearest the future's last price, ties lower) or a number."""
    exp = [e for e in monthly_expiries(inst) if e >= today.normalize()][0 if expiry == "near" else 1]
    if strike != "ATM":
        return exp, float(strike)
    fut = inst[(inst["instrument_type"] == "FUT") & (inst["expiry"] == exp)]["tradingsymbol"].iloc[0]
    forward = kite.quote([f"NFO:{fut}"])[f"NFO:{fut}"]["last_price"]
    strikes = inst[(inst["expiry"] == exp) & (inst["instrument_type"] == "CE")]["strike"].unique()
    return exp, float(min(strikes, key=lambda k: (abs(k - forward), k)))


def straddle_legs(kite, inst: pd.DataFrame, expiry: pd.Timestamp, strike: float, lots: int, side: str) -> list[Leg]:
    """Call and put at one strike, limit-priced at the touch (bid to sell, ask to buy)."""
    pair = inst[(inst["expiry"] == expiry) & (inst["strike"] == strike) & inst["instrument_type"].isin(["CE", "PE"])]
    if len(pair) != 2:
        raise ValueError(f"no call/put pair at {strike} for {expiry.date()}")
    quotes = kite.quote(list("NFO:" + pair["tradingsymbol"]))
    legs = []
    for _, row in pair.iterrows():
        depth = quotes[f"NFO:{row['tradingsymbol']}"]["depth"]
        bid, ask = depth["buy"][0]["price"], depth["sell"][0]["price"]
        if bid <= 0 or ask <= 0 or (ask - bid) / (ask + bid) > MAX_HALF_SPREAD:
            raise ValueError(f"{row['tradingsymbol']}: quote empty or too wide (bid {bid}, ask {ask})")
        legs.append(Leg(row["tradingsymbol"], side, int(lots * row["lot_size"]),
                        to_tick(bid if side == "SELL" else ask, side)))
    return legs


def blocked(s: KiteSettings, lots: int, live: bool, now: datetime, kill_switch: Path = KILL_SWITCH) -> list[str]:
    reasons = []
    if not live:
        reasons.append("--live not given")
    if not s.live_trading:
        reasons.append("KITE_LIVE_TRADING is not true")
    if kill_switch.exists():
        reasons.append(f"kill switch {kill_switch} present")
    if lots > s.max_lots:
        reasons.append(f"{lots} lots exceeds KITE_MAX_LOTS={s.max_lots}")
    t = now.astimezone(IST)
    if t.weekday() >= 5 or not MARKET_OPEN <= t.time() <= MARKET_CLOSE:
        reasons.append("outside NSE F&O hours")
    return reasons


def margin_shortfall(kite, legs: list[Leg]) -> float:
    params = [dict(exchange="NFO", tradingsymbol=leg.tradingsymbol, transaction_type=leg.transaction_type,
                   variety="regular", product="NRML", order_type="LIMIT", quantity=leg.quantity, price=leg.price)
              for leg in legs]
    need = kite.basket_order_margins(params)["final"]["total"]
    return max(0.0, need - kite.margins("equity")["net"])


def execute(kite, legs: list[Leg], s: KiteSettings, lots: int, live: bool, confirm=input, now: datetime | None = None,
            kill_switch: Path = KILL_SWITCH, log_path: Path | None = None) -> list[str]:
    """Send the legs if every guard passes; otherwise log a dry run. Returns the order ids sent."""
    now = now or datetime.now(IST)
    log_path = log_path or settings.data_dir / "live" / "orders.jsonl"
    record = {"time": now.isoformat(), "legs": [asdict(leg) for leg in legs]}

    def log(**fields) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({**record, **fields}, default=str) + "\n")

    reasons = blocked(s, lots, live, now, kill_switch)
    if not reasons:
        try:
            short = margin_shortfall(kite, legs)
            if short > 0:
                reasons.append(f"margin short by {short:,.0f}")
        except Exception as e:  # any failure of the margin check blocks the order
            reasons.append(f"margin check failed: {type(e).__name__}")
    text = " ; ".join(f"{leg.transaction_type} {leg.tradingsymbol} x{leg.quantity} @ {leg.price}" for leg in legs)
    if reasons:
        print(f"DRY RUN ({'; '.join(reasons)}): {text}")
        log(status="dry_run", reasons=reasons)
        return []
    if confirm(f"Type exactly to send:\n{text}\n> ").strip() != text:
        print("Confirmation did not match; nothing sent.")
        log(status="not_confirmed")
        return []
    ids = []
    for leg in legs:
        ids.append(kite.place_order(variety=KiteConnect.VARIETY_REGULAR, exchange=KiteConnect.EXCHANGE_NFO,
                                    tradingsymbol=leg.tradingsymbol, transaction_type=leg.transaction_type,
                                    quantity=leg.quantity, product=KiteConnect.PRODUCT_NRML,
                                    order_type=KiteConnect.ORDER_TYPE_LIMIT, price=leg.price,
                                    validity=KiteConnect.VALIDITY_DAY, tag="osr"))
        log(status="sent", tradingsymbol=leg.tradingsymbol, order_id=ids[-1])
    print(f"Sent {len(ids)} orders: {ids}")
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["straddle"])
    parser.add_argument("--side", choices=["SELL", "BUY"], required=True)
    parser.add_argument("--expiry", choices=["near", "next"], default="near")
    parser.add_argument("--strike", default="ATM")
    parser.add_argument("--lots", type=int, default=1)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    s, kite = KiteSettings(), client()
    inst = nifty_instruments(kite)
    expiry, strike = resolve(kite, inst, args.expiry, args.strike, pd.Timestamp.now(tz=IST).tz_localize(None))
    execute(kite, straddle_legs(kite, inst, expiry, strike, args.lots, args.side), s, args.lots, args.live)


if __name__ == "__main__":
    main()
