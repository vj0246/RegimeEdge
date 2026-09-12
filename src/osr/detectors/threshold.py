"""Percentile gate: stressed when a causal series (realised or implied volatility) exceeds its fit-window percentile."""

import numpy as np
import pandas as pd


class PercentileGate:
    def __init__(self, col: str, q: float = 80.0):
        self.col, self.q = col, q

    def fit(self, x: pd.DataFrame) -> None:
        self.threshold = np.percentile(x[self.col].to_numpy(), self.q)

    def stressed(self, x: pd.DataFrame) -> np.ndarray:
        return (self.score(x) > self.threshold).astype(int)

    def score(self, x: pd.DataFrame) -> np.ndarray:
        return x[self.col].to_numpy()

    def insample_stressed(self, x: pd.DataFrame) -> np.ndarray:
        return self.stressed(x)
