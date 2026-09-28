"""M0 acceptance tests (spec §12): closed forms vs brute-force enumeration,
EVSI identities, bounds, and distribution-fit sanity."""

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


# --- fit sanity (spec §3) ---------------------------------------------------

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
