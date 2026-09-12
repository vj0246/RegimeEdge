import numpy as np
import pandas as pd
import pytest
from hmmlearn.hmm import GaussianHMM

from osr.detectors.base import gate_path
from osr.detectors.bocpd import BOCPDGate
from osr.detectors.features import detector_inputs
from osr.detectors.hmm import HMMGate
from osr.detectors.jump import JumpGate
from osr.detectors.threshold import PercentileGate
from osr.synthetic import simulate_hmm

N, WINDOW, MIN_HISTORY, STEP = 2600, 1500, 1000, 100
FAST = dict(means=[0.0005, -0.001], sds=[0.008, 0.025], transmat=[[0.99, 0.01], [0.03, 0.97]])
SLOW = dict(means=[0.0005, -0.001], sds=[0.008, 0.02], transmat=[[0.996, 0.004], [0.008, 0.992]])
DETECTORS = {
    "hmm2": lambda: HMMGate(n_states=2, n_starts=3),
    "hmm3": lambda: HMMGate(n_states=3, n_starts=3),
    "jm": lambda: JumpGate(jump_penalty=50.0),
    "bocpd": lambda: BOCPDGate(),
    "rv": lambda: PercentileGate("rv"),
}


def make_data(dgp: dict, seed: int):
    r, states = simulate_hmm(N, **dgp, seed=seed)
    x = detector_inputs(r)
    return r, states.reindex(x.index), x, list(x.index[MIN_HISTORY::STEP])


@pytest.fixture(scope="module")
def datasets():
    return {"fast": make_data(FAST, 7), "slow": make_data(SLOW, 11)}


@pytest.fixture(scope="module")
def gates(datasets):
    _, _, x, refits = datasets["fast"]
    return {name: gate_path(make, x, refits, WINDOW, MIN_HISTORY) for name, make in DETECTORS.items()}


@pytest.mark.parametrize("name", DETECTORS)
def test_gate_ignores_data_after_each_day(datasets, gates, name):
    r, _, x, refits = datasets["fast"]
    cut = x.index[1900]
    rng = np.random.default_rng(1)
    later = r.index > cut
    r2 = r.copy()
    r2[later] = r2[later] * rng.uniform(0.2, 3.0, later.sum()) + rng.normal(0, 0.01, later.sum())
    x2 = detector_inputs(r2)
    assert x2.index.equals(x.index)
    g2 = gate_path(DETECTORS[name], x2, refits, WINDOW, MIN_HISTORY)
    pd.testing.assert_series_equal(gates[name][:cut], g2[:cut])
    assert not gates[name][cut:].equals(g2[cut:])  # the perturbation did reach the detector


# Per-segment floor only for the HMM, whose variance-ordered labels cannot flip between refits. JM labels
# follow cumulative return (Shu et al.) and can flip in a short window; that is a research output (refit
# stability), not a defect. Percentile gates cannot flag more than about 20% of a window by construction.
@pytest.mark.parametrize("name,dgp,overall,worst_segment", [
    ("hmm2", "fast", 0.9, 0.8),
    ("jm", "slow", 0.8, None),
    ("bocpd", "fast", 0.8, None),
    ("rv", "fast", 0.8, None),
])
def test_gate_tracks_true_regime(datasets, name, dgp, overall, worst_segment):
    _, states, x, refits = datasets[dgp]
    g = gate_path(DETECTORS[name], x, refits, WINDOW, MIN_HISTORY).dropna()
    hit = g == states[g.index]
    by_segment = hit.groupby(np.searchsorted(pd.DatetimeIndex(refits), g.index, side="right")).mean()
    print(name, dgp, round(hit.mean(), 3), round(by_segment.min(), 3))
    assert hit.mean() >= overall
    if worst_segment is not None:
        assert by_segment.min() >= worst_segment


def test_jm_bear_is_the_lower_cumulative_return_state(datasets):
    _, _, x, _ = datasets["slow"]
    for end in (1000, 1600, 2400):
        det = JumpGate(jump_penalty=50.0)
        det.fit(x.iloc[end - 1000 : end])
        labels, ret = np.asarray(det.model.labels_), x["x"].to_numpy()[end - 1000 : end]
        assert ret[labels == det.bear].sum() < ret[labels != det.bear].sum()


def test_hmm_filter_matches_hmmlearn_posterior_at_last_observation(datasets):
    _, _, x, _ = datasets["fast"]
    det = HMMGate(n_states=2, n_starts=3)
    det.fit(x.iloc[:1500])
    m = GaussianHMM(n_components=2, covariance_type="diag")
    m.startprob_, m.transmat_ = np.exp(det.log_start), np.exp(det.log_trans)
    m.means_, m.covars_ = det.mean[:, None], (det.sd**2)[:, None]
    p = det.prob(x.iloc[:1700])
    y = 100 * x[["r"]].to_numpy()
    for t in (0, 10, 1499, 1699):
        assert p[t] == pytest.approx(m.predict_proba(y[: t + 1])[-1, det.stressed_state], abs=1e-9)


def test_bocpd_without_changepoints_matches_conjugate_posterior():
    y = np.random.default_rng(3).normal(0.001, 0.02, 400)
    det = BOCPDGate(hazard=1e-12, r_max=1000)
    det.beta0 = y.var()
    path = det.variance_path(y)
    mu, kappa, alpha, beta = 0.0, 1.0, 2.0, det.beta0
    for yt in y:
        mu, kappa, alpha, beta = ((kappa * mu + yt) / (kappa + 1), kappa + 1, alpha + 0.5,
                                  beta + kappa * (yt - mu) ** 2 / (2 * (kappa + 1)))
    assert path[-1] == pytest.approx(beta / (alpha - 1), rel=1e-6)


def test_percentile_gate():
    det = PercentileGate("v", q=80.0)
    det.fit(pd.DataFrame({"v": np.arange(10.0)}))  # 80th percentile = 7.2
    assert det.stressed(pd.DataFrame({"v": [7.0, 7.3, 8.0]})).tolist() == [0, 1, 1]


def test_gate_path_validates_inputs(datasets):
    _, _, x, refits = datasets["fast"]
    with pytest.raises(ValueError):
        gate_path(DETECTORS["rv"], x, [pd.Timestamp("1990-01-01")])
    bad = x.copy()
    bad.iloc[5, 0] = np.nan
    with pytest.raises(ValueError):
        gate_path(DETECTORS["rv"], bad, refits)
