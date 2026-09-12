"""Bayesian online changepoint detection (Adams and MacKay 2007), normal-inverse-gamma prior.

The gate compares the posterior mean of the variance, averaged over run lengths, with its percentile
over the fit window. alpha0 = 2 makes the prior mean of the variance equal beta0, the window variance.
"""

import numpy as np
import pandas as pd
from scipy.special import gammaln


def student_t_logpdf(y: float, nu: np.ndarray, mu: np.ndarray, scale2: np.ndarray) -> np.ndarray:
    z = (y - mu) ** 2 / (nu * scale2)
    return gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(nu * np.pi * scale2) - (nu + 1) / 2 * np.log1p(z)


class BOCPDGate:
    def __init__(self, hazard: float = 1 / 250, r_max: int = 1000, pct: float = 80.0, col: str = "r"):
        self.hazard, self.r_max, self.pct, self.col = hazard, r_max, pct, col

    def variance_path(self, y: np.ndarray) -> np.ndarray:
        mu0, kappa0, alpha0, beta0 = 0.0, 1.0, 2.0, self.beta0
        w, mu, kappa, alpha, beta = (np.array([v]) for v in (1.0, mu0, kappa0, alpha0, beta0))
        out = np.empty(len(y))
        for t, yt in enumerate(y):
            logpred = student_t_logpdf(yt, 2 * alpha, mu, beta * (kappa + 1) / (alpha * kappa))
            pred = w * np.exp(logpred - logpred.max())
            w = np.concatenate(([pred.sum() * self.hazard], pred * (1 - self.hazard)))
            w /= w.sum()
            new_mu, new_beta = (kappa * mu + yt) / (kappa + 1), beta + kappa * (yt - mu) ** 2 / (2 * (kappa + 1))
            mu, beta = np.concatenate(([mu0], new_mu)), np.concatenate(([beta0], new_beta))
            kappa, alpha = np.concatenate(([kappa0], kappa + 1)), np.concatenate(([alpha0], alpha + 0.5))
            if len(w) > self.r_max + 1:
                w, mu, kappa, alpha, beta = (a[: self.r_max + 1] for a in (w, mu, kappa, alpha, beta))
                w /= w.sum()
            out[t] = (w * beta / (alpha - 1)).sum()
        return out

    def fit(self, x: pd.DataFrame) -> None:
        y = x[self.col].to_numpy()
        self.beta0 = y.var()
        self.threshold = np.percentile(self.variance_path(y), self.pct)

    def stressed(self, x: pd.DataFrame) -> np.ndarray:
        return (self.score(x) > self.threshold).astype(int)

    def score(self, x: pd.DataFrame) -> np.ndarray:
        return self.variance_path(x[self.col].to_numpy())

    def insample_stressed(self, x: pd.DataFrame) -> np.ndarray:
        return self.stressed(x)
