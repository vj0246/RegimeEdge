"""NIFTY contracts from Kite's NFO instrument dump: monthly expiries and the strikes around a forward."""

import numpy as np
import pandas as pd


def nifty_instruments(kite) -> pd.DataFrame:
    df = pd.DataFrame(kite.instruments("NFO"))
    df = df[(df["name"] == "NIFTY") & df["instrument_type"].isin(["FUT", "CE", "PE"])].copy()
    df["expiry"] = pd.to_datetime(df["expiry"])
    return df.reset_index(drop=True)


def monthly_expiries(inst: pd.DataFrame) -> list[pd.Timestamp]:
    """Monthly expiries are the ones futures carry; weekly options have none."""
    return sorted(pd.Timestamp(e) for e in inst.loc[inst["instrument_type"] == "FUT", "expiry"].unique())


def strikes_around(inst: pd.DataFrame, expiry: pd.Timestamp, forward: float, n: int) -> pd.DataFrame:
    """Calls and puts of one expiry at the n strikes either side of the strike nearest the forward."""
    chain = inst[(inst["expiry"] == expiry) & inst["instrument_type"].isin(["CE", "PE"])]
    strikes = np.sort(chain["strike"].unique())
    i = int(np.argmin(np.abs(strikes - forward)))
    return chain[chain["strike"].isin(strikes[max(0, i - n) : i + n + 1])]
