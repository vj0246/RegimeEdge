"""Black-76 straddle value and implied volatility on the future."""

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def straddle_value(forward: float, strike: float, t: float, r: float, sigma: float) -> float:
    s = sigma * np.sqrt(t)
    d1 = (np.log(forward / strike) + 0.5 * s * s) / s
    return np.exp(-r * t) * (forward * (2 * norm.cdf(d1) - 1) - strike * (2 * norm.cdf(d1 - s) - 1))


def straddle_iv(price: float, forward: float, strike: float, t: float, r: float) -> float:
    """NaN when the price is outside what volatilities between 0.1% and 500% can produce."""
    f = lambda sigma: straddle_value(forward, strike, t, r, sigma) - price  # noqa: E731
    lo, hi = 0.001, 5.0
    if t <= 0 or f(lo) > 0 or f(hi) < 0:
        return float("nan")
    return brentq(f, lo, hi, xtol=1e-10)
