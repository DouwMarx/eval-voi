"""Closed forms vs brute-force enumeration, EVSI identities, bounds, the
indifference value, the per-draw metrics, and distribution-fit sanity."""

import numpy as np
import pytest

from voi_rank import model
from voi_rank.fit import fit_beta, fit_lognormal


def brute_force(p, s, t, B, K):
    """Independent enumeration over (theta, x): joint distribution, posterior,
    argmax action, expected values. Utilities in the regret parameterization
    with u(theta, a=0) = 0, u(1,1) = B, u(0,1) = -K."""
    joint = {(1, 1): p * s, (1, 0): p * (1 - s),
             (0, 1): (1 - p) * (1 - t), (0, 0): (1 - p) * t}

    def expected_utility(belief, action):
        return belief * B - (1 - belief) * K if action == 1 else 0.0

    value_with_signal = 0.0
    for x in (0, 1):
        px = joint[(1, x)] + joint[(0, x)]
        if px == 0.0:
            continue
        posterior = joint[(1, x)] / px
        value_with_signal += px * max(expected_utility(posterior, 0),
                                      expected_utility(posterior, 1))
    value_prior = max(expected_utility(p, 0), expected_utility(p, 1))
    value_perfect = (p * max(expected_utility(1.0, 0), expected_utility(1.0, 1))
                     + (1 - p) * max(expected_utility(0.0, 0), expected_utility(0.0, 1)))
    return value_with_signal - value_prior, value_perfect - value_prior


def random_params(rng, n):
    p = rng.beta(0.5, 0.5, n)          # push mass toward the 0/1 edges
    s = rng.uniform(0, 1, n)
    t = rng.uniform(0, 1, n)
    B = rng.lognormal(np.log(1e4), 2.0, n)
    K = rng.lognormal(np.log(1e3), 2.0, n)
    return p, s, t, B, K


def test_matches_brute_force_1000_draws():
    # EVSI is a difference of near-cancelling terms of magnitude ~B, and the
    # closed form (P0 = 1 - P1, spec §2.3) and the enumeration (P0 as a joint
    # sum) order the arithmetic differently, so the 1e-12 tolerance is applied
    # relative to the utility scale max(1, B, K).
    rng = np.random.default_rng(0)
    p, s, t, B, K = random_params(rng, 1000)
    evsi, evpi = model.voi(p, s, t, B, K)
    for i in range(1000):
        bf_evsi, bf_evpi = brute_force(p[i], s[i], t[i], B[i], K[i])
        scale = max(1.0, B[i], K[i])
        assert abs(evsi[i] - bf_evsi) <= 1e-12 * scale
        assert abs(evpi[i] - bf_evpi) <= 1e-12 * scale


def test_evsi_zero_when_uninformative():
    rng = np.random.default_rng(1)
    p, s, _, B, K = random_params(rng, 200)
    t = 1.0 - s  # signal carries no information about theta
    evsi, evpi = model.voi(p, s, t, B, K)
    assert np.all(evsi <= 1e-10 * np.maximum(1.0, evpi))


def test_evsi_equals_evpi_when_perfect():
    rng = np.random.default_rng(2)
    p, _, _, B, K = random_params(rng, 200)
    ones = np.ones_like(p)
    evsi, evpi = model.voi(p, ones, ones, B, K)
    scale = np.maximum(1.0, np.maximum(B, K))
    assert np.all(np.abs(evsi - evpi) <= 1e-12 * scale)


def test_bounds_always_hold():
    rng = np.random.default_rng(3)
    p, s, t, B, K = random_params(rng, 5000)
    evsi, evpi = model.voi(p, s, t, B, K)
    assert np.all(evsi >= 0.0)
    assert np.all(evsi <= evpi)
    assert np.all(np.isfinite(evsi)) and np.all(np.isfinite(evpi))


def test_degenerate_edges_no_nan():
    for p, s, t in [(0.0, 1.0, 1.0), (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]:
        evsi, evpi = model.voi(p, s, t, 100.0, 10.0)
        assert np.isfinite(evsi) and np.isfinite(evpi)
        assert 0.0 <= evsi <= evpi + 1e-15


def test_indifference_value_is_the_maximum_over_the_threshold():
    """EVSI° = (B+K) p(1-p)(s+t-1) is EVSI maximised over pi* = K/(B+K) at
    fixed stakes: no split of the stakes beats it, and the split K = (1-p)
    Lambda (pi* = p) reaches it."""
    rng = np.random.default_rng(4)
    p, s, t, _, _ = random_params(rng, 300)
    s, t = np.maximum(s, 1 - t) + 1e-3, t          # informative: s + t > 1
    s = np.minimum(s, 1.0)
    lam = rng.lognormal(np.log(1e5), 1.0, 300)
    ind = model.voi_indifference(p, s, t, lam * 0.3, lam * 0.7)   # the stakes split does not matter
    assert np.allclose(ind, lam * p * (1 - p) * (s + t - 1))
    for pi_star in np.linspace(0.01, 0.99, 25):
        evsi, _ = model.voi(p, s, t, lam * (1 - pi_star), lam * pi_star)
        assert np.all(evsi <= ind * (1 + 1e-9) + 1e-9 * lam)
    evsi_at_p, _ = model.voi(p, s, t, lam * (1 - p), lam * p)
    assert np.allclose(evsi_at_p, ind, rtol=1e-9, atol=1e-9 * lam.max())
    assert model.voi_indifference(0.5, 0.2, 0.3, 1.0, 1.0) == pytest.approx(2 * 0.25 * 0.5)   # |s+t-1|


def test_metrics_derived_per_draw():
    draws = {"p": np.array([0.3, 0.3, 0.01]), "s": np.array([0.9, 0.9, 0.9]), "t": np.array([0.9, 0.9, 0.9]),
             "B": np.array([1e5, 1e5, 1e5]), "K": np.array([1e4, 1e4, 1e4]),
             "C_build": np.array([5e3, 5e3, 5e3]), "C_run": np.array([1e3, 1e3, 1e3]),
             "n": np.array([10.0, 1.0, 10.0])}
    m = model.metrics(draws)
    assert list(m) == model.METRIC_NAMES == ["EVSI", "EVPI", "EVSI_ind", "C", "eta", "eta_ind", "eta_run",
                                             "net_n", "eta_n", "n_star", "pays"]
    evsi, evpi = model.voi(draws["p"], draws["s"], draws["t"], draws["B"], draws["K"])
    assert np.array_equal(m["EVSI"], evsi) and np.array_equal(m["EVPI"], evpi)
    assert np.array_equal(m["C"], np.array([6e3, 6e3, 6e3]))
    assert np.allclose(m["eta"], evsi / 6e3) and np.allclose(m["eta_run"], evsi / 1e3)
    assert np.allclose(m["eta_ind"], model.voi_indifference(draws["p"], 0.9, 0.9, 1e5, 1e4) / 6e3)
    assert np.allclose(m["net_n"], draws["n"] * evsi - 5e3 - draws["n"] * 1e3)
    assert np.allclose(m["eta_n"], draws["n"] * evsi / (5e3 + draws["n"] * 1e3))
    # draw 0: EVSI > C_run (p = 0.3 is inside the decision-changing region), n* = C_build / (EVSI - C_run)
    assert evsi[0] > 1e3 and m["n_star"][0] == pytest.approx(5e3 / (evsi[0] - 1e3))
    assert m["pays"][0] == 1.0 and m["pays"][1] == 0.0   # 10 reuses pay, one does not
    # draw 2: p = 0.01, the developer deploys regardless, EVSI = 0 <= C_run: n* infinite, never pays
    assert evsi[2] == 0.0 and m["n_star"][2] == np.inf and m["pays"][2] == 0.0
    assert np.all(np.isfinite(m["eta"])) and m["eta"][2] == 0.0


# --- fit sanity -------------------------------------------------------------

def test_fit_rejects_non_monotone():
    with pytest.raises(ValueError):
        fit_lognormal(10.0, 5.0, 100.0)
    with pytest.raises(ValueError):
        fit_beta(0.5, 0.5, 0.9)


def test_lognormal_roundtrip():
    from scipy import stats
    mu, sigma = np.log(150e3), 1.2
    q05, q50, q95 = stats.lognorm.ppf([0.05, 0.5, 0.95], s=sigma, scale=np.exp(mu))
    res = fit_lognormal(q05, q50, q95)
    assert abs(res.params["mu"] - mu) < 1e-6
    assert abs(res.params["sigma"] - sigma) < 1e-6
    assert not res.warning


def test_beta_roundtrip():
    from scipy import stats
    a, b = 2.5, 7.0
    q05, q50, q95 = stats.beta.ppf([0.05, 0.5, 0.95], a, b)
    res = fit_beta(q05, q50, q95)
    refit_q = stats.beta.ppf([0.05, 0.5, 0.95], res.params["alpha"], res.params["beta"])
    assert np.allclose(refit_q, [q05, q50, q95], atol=1e-3)
    assert res.residual < 0.02 and not res.warning


def test_lognormal_asymmetry_warning():
    # log-quantiles heavily right-skewed relative to a lognormal
    res = fit_lognormal(90.0, 100.0, 10000.0)
    assert res.warning


def test_beta_fit_survives_extremely_tight_triple():
    # moment-matched init lands above the optimizer bound; must clip, not crash
    res = fit_beta(0.4999, 0.5, 0.5001)
    assert res.family == "beta" and np.isfinite(res.residual)


def test_rank_stability_zero_ties_do_not_count():
    from voi_rank.sensitivity import rank_stability
    eff = np.zeros((5, 100))
    eff[3] = 1.0  # only one scenario ever positive
    p = rank_stability(eff, top=3)
    assert p[3] == 1.0
    assert np.all(p[[0, 1, 2, 4]] == 0.0)
    assert rank_stability(eff).shape == (5,)   # the default top is 5 (p_top5)
