"""Track T: long Nifty 50 TRI, flat into cash when gated (decisions.md section 6)."""

import numpy as np
import pandas as pd


def tri_returns(tri: pd.Series, rf: pd.Series, gate: pd.Series | None = None, lag: int = 1,
                buy: float = 0.0, sell: float = 0.0) -> pd.Series:
    """Daily returns. A signal at the close of t moves the position at the close of t+lag, so the position
    held over day u is 1 - gate[u-1-lag]. Switching costs are charged on the trade day. gate=None is buy and
    hold without costs; missing signals count as invested."""
    r = tri.pct_change()
    if gate is None:
        return r.rename("ret")
    after_close = 1 - gate.reindex(tri.index).fillna(0.0).shift(lag).fillna(0.0)
    held = after_close.shift(1).fillna(1.0)
    trade = after_close.diff().fillna(0.0)
    cost = np.where(trade > 0, buy, 0.0) + np.where(trade < 0, sell, 0.0)
    return (held * r + (1 - held) * rf.reindex(tri.index) - cost).rename("ret")
