"""Performance metrics and inference (decisions.md sections 9 to 11). Returns are daily simple returns."""

import math
from collections.abc import Callable
from itertools import combinations

import numpy as np
import pandas as pd
from arch.bootstrap import optimal_block_length
from scipy.stats import kurtosis, norm, skew
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples

PERIODS = 252
EULER_GAMMA = 0.5772156649015329
SEED = 20260912


def sharpe(r: np.ndarray, rf: np.ndarray) -> float:
    x = r - rf
    return x.mean() / x.std(ddof=1) * math.sqrt(PERIODS)


def mppm(r: np.ndarray, rf: np.ndarray, rho: float = 3.0) -> float:
    """Manipulation-proof performance measure (Goetzmann, Ingersoll, Spiegel and Welch 2007), annualised."""
    return math.log((((1 + r) / (1 + rf)) ** (1 - rho)).mean()) / ((1 - rho) / PERIODS)


def max_drawdown(r: np.ndarray) -> float:
    wealth = np.cumprod(1 + r)
    return float((wealth / np.maximum.accumulate(wealth) - 1).min())


def cvar(r: np.ndarray, level: float = 0.95) -> float:
    """Mean of the worst (1 - level) share of daily returns."""
    return float(r[r <= np.quantile(r, 1 - level)].mean())


def summary(r: np.ndarray, rf: np.ndarray) -> dict[str, float]:
    return {
        "ann_return": float(np.prod(1 + r) ** (PERIODS / len(r)) - 1),
        "ann_vol": float(r.std(ddof=1) * math.sqrt(PERIODS)),
        "sharpe": sharpe(r, rf),
        "mppm": mppm(r, rf),
        "max_drawdown": max_drawdown(r),
        "cvar95": cvar(r),
        "skew": float(skew(r)),
    }


def circular_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    starts = rng.integers(0, n, size=math.ceil(n / block))
    return ((starts[:, None] + np.arange(block)[None, :]) % n).ravel()[:n]


def block_length(x: np.ndarray) -> int:
    """Politis and White (2004) automatic block length for the circular bootstrap."""
    return max(1, int(round(optimal_block_length(x)["circular"].iloc[0])))


def paired_difference_test(r1: np.ndarray, r2: np.ndarray, rf: np.ndarray,
                           metric: Callable[[np.ndarray, np.ndarray], float],
                           n_boot: int = 10_000, seed: int = SEED) -> dict[str, float]:
    """metric(r1) - metric(r2) by paired circular block bootstrap: 95% percentile interval and the two-sided
    p-value, share of resamples with |d* - d| >= |d|."""
    d = metric(r1, rf) - metric(r2, rf)
    block = block_length(r1 - r2)
    rng = np.random.default_rng(seed)
    boot = np.empty(n_boot)
    for b in range(n_boot):
        i = circular_block_indices(len(r1), block, rng)
        boot[b] = metric(r1[i], rf[i]) - metric(r2[i], rf[i])
    return {"diff": d, "ci_low": float(np.quantile(boot, 0.025)), "ci_high": float(np.quantile(boot, 0.975)),
            "p_value": float(np.mean(np.abs(boot - d) >= abs(d))), "block": block}


def sharpe_diff_and_se(x1: np.ndarray, x2: np.ndarray) -> tuple[float, float]:
    """Per-period Sharpe difference of excess returns and its delta-method HAC (Newey-West) standard error."""
    m1, m2, g1, g2 = x1.mean(), x2.mean(), (x1**2).mean(), (x2**2).mean()
    v1, v2 = g1 - m1**2, g2 - m2**2
    grad = np.array([g1 / v1**1.5, -g2 / v2**1.5, -m1 / (2 * v1**1.5), m2 / (2 * v2**1.5)])
    y = np.column_stack([x1 - m1, x2 - m2, x1**2 - g1, x2**2 - g2])
    n = len(y)
    lags = int(4 * (n / 100) ** (2 / 9))
    psi = y.T @ y / n
    for lag in range(1, lags + 1):
        c = y[lag:].T @ y[:-lag] / n
        psi += (1 - lag / (lags + 1)) * (c + c.T)
    return m1 / math.sqrt(v1) - m2 / math.sqrt(v2), math.sqrt(grad @ psi @ grad / n)


def sharpe_difference_test(r1: np.ndarray, r2: np.ndarray, rf: np.ndarray, n_boot: int = 10_000,
                           seed: int = SEED) -> dict[str, float]:
    """Ledoit and Wolf (2008): studentised paired circular block bootstrap for the Sharpe difference
    (annualised); Newey-West HAC standard errors in place of their prewhitened kernel."""
    x1, x2 = r1 - rf, r2 - rf
    d, se = sharpe_diff_and_se(x1, x2)
    block = block_length(r1 - r2)
    rng = np.random.default_rng(seed)
    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        i = circular_block_indices(len(x1), block, rng)
        d_b, se_b = sharpe_diff_and_se(x1[i], x2[i])
        t_boot[b] = (d_b - d) / se_b
    q, ann = np.quantile(np.abs(t_boot), 0.95), math.sqrt(PERIODS)
    return {"diff": d * ann, "se": se * ann, "ci_low": (d - q * se) * ann, "ci_high": (d + q * se) * ann,
            "p_value": float(np.mean(np.abs(t_boot) >= abs(d / se))), "block": block}


def circular_shift_test(run: Callable[[np.ndarray], float], gate: np.ndarray, n: int = 999, seed: int = SEED,
                        margin: int = 252) -> dict[str, float]:
    """One-sided test that a gate's timing beats rotations of itself. run(gate) returns the metric."""
    observed = run(gate)
    rng = np.random.default_rng(seed)
    null = np.array([run(np.roll(gate, k)) for k in rng.integers(margin, len(gate) - margin + 1, size=n)])
    return {"observed": observed, "null_mean": float(null.mean()),
            "p_value": float((1 + np.sum(null >= observed)) / (n + 1))}


def expected_max_sharpe(n_trials: float, var_sharpe: float) -> float:
    """Expected maximum per-period Sharpe of n_trials unskilled trials (Bailey and Lopez de Prado 2014)."""
    if n_trials <= 1:
        return 0.0
    z = (1 - EULER_GAMMA) * norm.ppf(1 - 1 / n_trials) + EULER_GAMMA * norm.ppf(1 - 1 / (n_trials * math.e))
    return math.sqrt(var_sharpe) * z


def probabilistic_sharpe(x: np.ndarray, sr0: float) -> float:
    """P(true per-period Sharpe > sr0) for excess returns x; with sr0 from expected_max_sharpe this is the DSR."""
    sr = x.mean() / x.std(ddof=1)
    g3, g4 = skew(x), kurtosis(x, fisher=False)
    return float(norm.cdf((sr - sr0) * math.sqrt(len(x) - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2)))


def effective_trials(excess: pd.DataFrame, seed: int = 0) -> tuple[int, np.ndarray, float]:
    """One level of ONC (Lopez de Prado and Lewis 2019): k-means on the correlation-distance matrix, k by the
    silhouette t-statistic. Returns (k, labels, variance of cluster Sharpe ratios per period); clusters are
    equal-weighted averages of their members."""
    corr = excess.corr().to_numpy()
    dist = np.sqrt(np.clip(0.5 * (1 - corr), 0.0, None))
    np.fill_diagonal(dist, 0.0)
    best_q, labels = -np.inf, np.zeros(len(corr), dtype=int)
    for k in range(2, len(corr)):
        lab = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(dist)
        s = silhouette_samples(dist, lab, metric="precomputed")
        q = s.mean() / s.std() if s.std() > 0 else np.inf
        if q > best_q:
            best_q, labels = q, lab
    k = int(labels.max() + 1)
    clusters = np.column_stack([excess.to_numpy()[:, labels == c].mean(axis=1) for c in range(k)])
    srs = clusters.mean(axis=0) / clusters.std(axis=0, ddof=1)
    return k, labels, float(srs.var(ddof=1)) if k > 1 else 0.0


def pbo_cscv(returns: np.ndarray, rf: np.ndarray, metric: str = "sharpe", n_blocks: int = 16,
             rho: float = 3.0) -> float:
    """Probability of backtest overfitting by combinatorially symmetric cross-validation (Bailey, Borwein,
    Lopez de Prado and Zhu 2017) on a T x N matrix of trial returns: share of splits whose in-sample best
    trial ranks at or below the out-of-sample median."""
    n_obs, n_trials = returns.shape
    edges = np.linspace(0, n_obs, n_blocks + 1).astype(int)
    blocks = list(zip(edges[:-1], edges[1:]))
    if metric == "sharpe":
        x = returns - rf[:, None]
        stats = np.stack([np.stack([x[a:b].sum(0), (x[a:b] ** 2).sum(0), np.full(n_trials, b - a)]) for a, b in blocks])

        def value(s: np.ndarray) -> np.ndarray:
            m = s[0] / s[2]
            return m / np.sqrt(s[1] / s[2] - m**2)
    else:
        u = ((1 + returns) / (1 + rf[:, None])) ** (1 - rho)
        stats = np.stack([np.stack([u[a:b].sum(0), np.full(n_trials, b - a)]) for a, b in blocks])

        def value(s: np.ndarray) -> np.ndarray:
            return np.log(s[0] / s[1]) / ((1 - rho) / PERIODS)

    total = stats.sum(0)
    below = []
    for split in combinations(range(n_blocks), n_blocks // 2):
        is_stats = stats[list(split)].sum(0)
        best = np.argmax(value(is_stats))
        oos = value(total - is_stats)
        rank = 1 + np.sum(oos < oos[best])
        below.append(rank / (n_trials + 1) <= 0.5)
    return float(np.mean(below))
