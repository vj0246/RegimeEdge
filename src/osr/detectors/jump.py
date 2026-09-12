"""Statistical jump model gate (Shu, Yu and Mulvey 2024): standardised features, online DP state."""

import numpy as np
import pandas as pd
from jumpmodels.jump import JumpModel

FEATURES = ["dd10", "sortino20", "sortino60"]


class JumpGate:
    def __init__(self, jump_penalty: float, ret_col: str = "x", seed: int = 0):
        self.jump_penalty, self.ret_col, self.seed = jump_penalty, ret_col, seed

    def fit(self, x: pd.DataFrame) -> None:
        f = x[FEATURES]
        self.mu, self.sd = f.mean(), f.std()
        self.model = JumpModel(n_components=2, jump_penalty=self.jump_penalty, random_state=self.seed)
        self.model.fit((f - self.mu) / self.sd, ret_ser=x[self.ret_col], sort_by="cumret")
        labels = np.asarray(self.model.labels_)
        ret = x[self.ret_col].to_numpy()
        self.bear = int(np.argmin([ret[labels == k].sum() for k in (0, 1)]))

    def stressed(self, x: pd.DataFrame) -> np.ndarray:
        labels = np.asarray(self.model.predict_online((x[FEATURES] - self.mu) / self.sd))
        return (labels == self.bear).astype(int)

    def insample_stressed(self, x: pd.DataFrame) -> np.ndarray:
        """DP path over all of x. Refit diagnostics only, never a trading signal."""
        labels = np.asarray(self.model.predict((x[FEATURES] - self.mu) / self.sd))
        return (labels == self.bear).astype(int)
