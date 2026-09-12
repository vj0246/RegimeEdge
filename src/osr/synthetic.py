"""Synthetic return series with known regimes, for detector tests and validation (PLAN.md Phase 3)."""

from collections.abc import Sequence

import numpy as np
import pandas as pd


def simulate_hmm(n: int, means: Sequence[float], sds: Sequence[float], transmat: Sequence[Sequence[float]],
                 seed: int = 0, start: str = "2000-01-03") -> tuple[pd.Series, pd.Series]:
    """Gaussian HMM returns and their true states on a business-day index; starts in state 0."""
    rng = np.random.default_rng(seed)
    cum = np.cumsum(np.asarray(transmat, dtype=float), axis=1)
    u = rng.random(n)
    states = np.zeros(n, dtype=int)
    for t in range(1, n):
        states[t] = min(np.searchsorted(cum[states[t - 1]], u[t], side="right"), len(means) - 1)
    r = rng.normal(np.asarray(means)[states], np.asarray(sds)[states])
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(r, idx, name="r"), pd.Series(states, idx, name="state")


def simulate_hsmm_t(n: int, means: Sequence[float], sds: Sequence[float], mean_durations: Sequence[float],
                    shape: float = 2.0, nu: float = 4.0, seed: int = 0,
                    start: str = "2000-01-03") -> tuple[pd.Series, pd.Series]:
    """Two alternating states with shifted negative-binomial durations and unit-variance Student-t shocks."""
    rng = np.random.default_rng(seed)
    states = np.empty(n, dtype=int)
    t, k = 0, 0
    while t < n:
        p = shape / (shape + mean_durations[k] - 1)  # 1 + NB(shape, p) has mean mean_durations[k]
        d = 1 + rng.negative_binomial(shape, p)
        states[t : t + d] = k
        t, k = t + d, 1 - k
    z = rng.standard_t(nu, n) * np.sqrt((nu - 2) / nu)
    r = np.asarray(means)[states] + np.asarray(sds)[states] * z
    idx = pd.bdate_range(start, periods=n)
    return pd.Series(r, idx, name="r"), pd.Series(states, idx, name="state")


def simulate_garch_t(n: int, mu: float, omega: float, alpha: float, beta: float, nu: float, seed: int = 0,
                     burn: int = 500, start: str = "2000-01-03") -> pd.Series:
    """GARCH(1,1) with unit-variance Student-t shocks and no regimes. Parameters in percent units (as the arch
    package fits 100 x returns); returns are fractions."""
    rng = np.random.default_rng(seed)
    z = rng.standard_t(nu, n + burn) * np.sqrt((nu - 2) / nu)
    out = np.empty(n + burn)
    var, eps = omega / (1 - alpha - beta), 0.0
    for t in range(n + burn):
        var = omega + alpha * eps**2 + beta * var
        eps = np.sqrt(var) * z[t]
        out[t] = mu + eps
    return pd.Series(out[burn:] / 100, pd.bdate_range(start, periods=n), name="r")
