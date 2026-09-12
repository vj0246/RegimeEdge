"""Gaussian HMM gate: EM with restarts, forward-filtered probability of the highest-variance state."""

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
from scipy.stats import norm


class HMMGate:
    def __init__(self, n_states: int = 2, n_starts: int = 10, threshold: float = 0.5, col: str = "r",
                 scale: float = 100.0):
        self.n_states, self.n_starts, self.threshold, self.col, self.scale = n_states, n_starts, threshold, col, scale

    def fit(self, x: pd.DataFrame) -> None:
        y = self.scale * x[[self.col]].to_numpy()
        best_ll, best = -np.inf, None
        for seed in range(self.n_starts):
            m = GaussianHMM(n_components=self.n_states, covariance_type="diag", n_iter=1000, tol=1e-6,
                            random_state=seed)
            m.fit(y)
            ll = m.score(y)
            if ll > best_ll:
                best_ll, best = ll, m
        self.model = best
        var = best.covars_[:, 0, 0]
        self.stressed_state = int(np.argmax(var))
        self.mean, self.sd = best.means_[:, 0], np.sqrt(var)
        with np.errstate(divide="ignore"):
            self.log_start, self.log_trans = np.log(best.startprob_), np.log(best.transmat_)

    def prob(self, x: pd.DataFrame) -> np.ndarray:
        """Filtered P(stressed state at t | observations up to t) with frozen parameters."""
        y = self.scale * x[self.col].to_numpy()
        loglik = norm.logpdf(y[:, None], self.mean[None, :], self.sd[None, :])
        out = np.empty(len(y))
        alpha = self.log_start + loglik[0]
        for t in range(len(y)):
            if t:
                alpha = logsumexp(alpha[:, None] + self.log_trans, axis=0) + loglik[t]
            alpha = alpha - logsumexp(alpha)
            out[t] = np.exp(alpha[self.stressed_state])
        return out

    def stressed(self, x: pd.DataFrame) -> np.ndarray:
        return (self.prob(x) > self.threshold).astype(int)

    def score(self, x: pd.DataFrame) -> np.ndarray:
        return self.prob(x)

    def insample_stressed(self, x: pd.DataFrame) -> np.ndarray:
        """Viterbi path over all of x. Refit diagnostics only, never a trading signal."""
        return (self.model.predict(self.scale * x[[self.col]].to_numpy()) == self.stressed_state).astype(int)
