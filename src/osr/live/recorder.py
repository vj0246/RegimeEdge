"""Spread recorder: one snapshot of NIFTY monthly quotes (five-level bid/ask depth, OI) around the forward.

  python -m osr.live.recorder [--strikes 5]    writes data/live/quotes/<IST timestamp>.parquet

Run near the close (about 15:20 IST) on trading days, e.g. from Windows Task Scheduler. The snapshots build a
measured half-spread series to replace the assumed cost tiers in later work.
"""

import argparse
import time

import numpy as np
import pandas as pd

from osr.config import settings
from osr.live.instruments import monthly_expiries, nifty_instruments, strikes_around
from osr.live.session import client

INDEX = "NSE:NIFTY 50"
QUOTE_PAUSE_S = 1.1  # Kite allows one quote request a second
DEPTH = 5


def flatten(quotes: dict) -> pd.DataFrame:
    """Kite quote payload -> one row per instrument, depth levels as columns, mid and half-spread."""
    rows = []
    for key, q in quotes.items():
        row = {"symbol": key, "last_price": q.get("last_price"), "volume": q.get("volume"), "oi": q.get("oi"),
               "quote_time": q.get("timestamp")}
        for side, name in (("buy", "bid"), ("sell", "ask")):
            for i, level in enumerate(q.get("depth", {}).get(side, [])[:DEPTH], 1):
                row[f"{name}{i}"], row[f"{name}{i}_qty"] = level["price"], level["quantity"]
        rows.append(row)
    out = pd.DataFrame(rows)
    for col in ("bid1", "ask1"):
        if col not in out:
            out[col] = np.nan
    quoted = (out["bid1"] > 0) & (out["ask1"] > 0)
    out["mid"] = ((out["bid1"] + out["ask1"]) / 2).where(quoted)
    out["half_spread_pct"] = (out["ask1"] - out["bid1"]) / 2 / out["mid"]
    return out


def snapshot(kite, n_strikes: int = 5, pause_s: float = QUOTE_PAUSE_S) -> pd.DataFrame:
    """Index, near and next monthly futures, and calls and puts at n strikes either side of each forward."""
    inst = nifty_instruments(kite)
    futs = inst[(inst["instrument_type"] == "FUT") & inst["expiry"].isin(monthly_expiries(inst)[:2])]
    first = kite.quote([INDEX, *("NFO:" + futs["tradingsymbol"])])
    opts = pd.concat([strikes_around(inst, f["expiry"], first[f"NFO:{f['tradingsymbol']}"]["last_price"], n_strikes)
                      for _, f in futs.iterrows()], ignore_index=True)
    time.sleep(pause_s)
    second = kite.quote(list("NFO:" + opts["tradingsymbol"]))
    meta = pd.concat([futs, opts], ignore_index=True)
    meta["symbol"] = "NFO:" + meta["tradingsymbol"]
    rows = flatten({**first, **second}).merge(meta[["symbol", "instrument_type", "expiry", "strike", "lot_size"]],
                                              on="symbol", how="left")
    return rows.assign(snapshot_time=pd.Timestamp.now(tz="Asia/Kolkata"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strikes", type=int, default=5)
    args = parser.parse_args()
    df = snapshot(client(), args.strikes)
    out = settings.data_dir / "live" / "quotes"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{df['snapshot_time'].iloc[0]:%Y%m%d_%H%M%S}.parquet"
    df.to_parquet(path, index=False)
    near = df[df["instrument_type"].isin(["CE", "PE"]) & (df["expiry"] == df["expiry"].min())]
    print(f"{path}: {len(df)} quotes; near-month option half-spread median {near['half_spread_pct'].median():.2%} of mid")


if __name__ == "__main__":
    main()
