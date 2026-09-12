"""Causal detector inputs: each value uses data up to that day only."""

import numpy as np
import pandas as pd


def detector_inputs(r: pd.Series, rf: pd.Series | float = 0.0) -> pd.DataFrame:
    """Every gate's inputs: r (log return), x (excess return), rv (21-day realised vol), JM features.
    Warm-up rows are dropped."""
    x = r - rf
    return pd.concat([r.rename("r"), x.rename("x"), realized_vol(r).rename("rv"), jm_features(x)], axis=1).dropna()


def realized_vol(r: pd.Series, n: int = 21) -> pd.Series:
    """Annualised root mean square of the last n daily log returns."""
    return np.sqrt(252 * (r**2).rolling(n).mean())


def jm_features(x: pd.Series) -> pd.DataFrame:
    """Shu, Yu and Mulvey (2024) Table 2: EWM downside deviation (halflife 10), EWM Sortino ratios (20, 60)."""
    down2 = x.clip(upper=0) ** 2
    dd = {hl: np.sqrt(down2.ewm(halflife=hl, min_periods=hl).mean()) for hl in (10, 20, 60)}
    features = pd.DataFrame({
        "dd10": dd[10],
        "sortino20": x.ewm(halflife=20, min_periods=20).mean() / dd[20],
        "sortino60": x.ewm(halflife=60, min_periods=60).mean() / dd[60],
    })
    return features.replace([np.inf, -np.inf], np.nan)
