"""Causal gate paths: refit on a trailing window at given dates, infer daily with frozen parameters."""

from collections.abc import Callable, Sequence
from typing import Protocol

import numpy as np
import pandas as pd


class Detector(Protocol):
    def fit(self, x: pd.DataFrame) -> None: ...

    def stressed(self, x: pd.DataFrame) -> np.ndarray:
        """0/1 per row of x; the value for row i may depend on rows up to and including i only."""
        ...


def majority_filter(gate: pd.Series, k: int) -> pd.Series:
    """Shu, Yu and Mulvey (2024) k-day filter: stressed only when more than half of the last k raw states were."""
    share = gate.rolling(k, min_periods=k).mean()
    return (share > 0.5).astype(float).where(share.notna())


def gate_path(
    make: Callable[[], Detector],
    x: pd.DataFrame,
    refit_dates: Sequence[pd.Timestamp],
    window: int | None = 3000,
    min_history: int = 1500,
    method: str = "stressed",
) -> pd.Series:
    """Gate state per day. The fit made at the close of a refit date covers that day up to the next refit.

    window=None means an expanding window. Days before the first fit with min_history rows are NaN.
    method="score" returns a detector's continuous score instead of its 0/1 state.
    """
    if x.isna().to_numpy().any():
        raise ValueError("inputs contain NaN; drop warm-up rows first")
    pos = x.index.get_indexer(pd.DatetimeIndex(refit_dates))
    if (pos < 0).any():
        raise ValueError("every refit date must be a row of x")
    gate = pd.Series(np.nan, index=x.index, name="gate")
    bounds = [*sorted(pos), len(x)]
    for p, nxt in zip(bounds[:-1], bounds[1:]):
        start = 0 if window is None else max(0, p + 1 - window)
        if p + 1 - start < min_history:
            continue
        det = make()
        det.fit(x.iloc[start : p + 1])
        gate.iloc[p:nxt] = getattr(det, method)(x.iloc[start:nxt])[p - start :]
    return gate
