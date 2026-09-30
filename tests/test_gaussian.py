"""Gaussian-state family (spec v2.1): closed forms against numerical
integration, the action-model identities of the chapter, the over-determined
fit with its residuals and warnings, and the payload validation."""

import copy
import re
from pathlib import Path

import numpy as np
import pytest
from scipy import integrate, optimize, stats

from tests.test_gauss_pipeline import STUDY_DIRS
from voi_rank import gauss_fit, model
from voi_rank import gaussian as g
from voi_rank.fit import GAUSS_PARAM_NAMES

B, K = 150e3, 10e3
LAMBDA = B + K
ROOT = Path(__file__).resolve().parent.parent


# --- numerical references ------------------------------------------------------

def step_bruteforce(d, R2, B, K):
    """eq. stepcont by brute force over y and the posterior: integrate the
    density of y ~ N(mu0, sigma0^2 + r) against V(pi(y)) with
    pi(y) = Phi((mu1(y) - theta_c) / sigma1), then subtract V(p)."""
    sigma0, mu0, theta_c = 1.0, 0.0, -d
    r = (1.0 / R2 - 1.0) * sigma0**2
    sd_y = np.sqrt(sigma0**2 + r)
    s1 = sigma0 * np.sqrt(1.0 - R2)

    def integrand(y):
        mu1 = mu0 + R2 * (y - mu0)
        pi = stats.norm.cdf((mu1 - theta_c) / s1)
        return stats.norm.pdf(y, mu0, sd_y) * model.value_of_acting(pi, B, K)

    val = integrate.quad(integrand, -12 * sd_y, 12 * sd_y, limit=400, epsabs=1e-10, epsrel=1e-11)[0]
    return val - float(model.value_of_acting(stats.norm.cdf(d), B, K))


def s_tail_reference(d, R2, c):
    """s = P(w > c | u > -d) by the 1-D integral over u with the tail density
    ratio taken in logs (independent of gaussian._tail_s: no substitution to
    the excess, plain quad over u on a finite window)."""
    R, s1 = np.sqrt(R2), np.sqrt(1 - R2)
    a = -d
    f = lambda u: np.exp(stats.norm.logpdf(u) - stats.norm.logcdf(-a)) * stats.norm.cdf((R * u - c) / s1)  # noqa: E731
    return integrate.quad(f, a, a + 60.0 / max(a, 1.0), epsabs=0, epsrel=1e-12, limit=200)[0]


def expected_loss_at(m, sigma, k, c_minus, c_plus):
    """Expected loss of acting m sd above the mean of a N(., sigma^2) belief
    under the loss c_- |a - theta|^k (a < theta) / c_+ |a - theta|^k (a > theta),
    by quadrature over z."""
    f = lambda z: (c_plus if z < m else c_minus) * abs(sigma * (z - m)) ** k * stats.norm.pdf(z)  # noqa: E731
    return integrate.quad(f, -np.inf, m)[0] + integrate.quad(f, m, np.inf)[0]


def min_loss(sigma, k, c_minus, c_plus):
    """(minimal expected loss, optimal shift m* in sd units): the chapter's
    c_k sigma^k, by an independent scalar minimisation of the quadrature."""
    res = optimize.minimize_scalar(expected_loss_at, bounds=(-8, 8), args=(sigma, k, c_minus, c_plus),
                                   method="bounded", options={"xatol": 1e-9})
    return res.fun, res.x


# --- closed forms vs numerics ---------------------------------------------------

def test_bvn_cdf_matches_scipy_including_edges():
    rng = np.random.default_rng(0)
    for _ in range(200):
        h, k = rng.normal(0, 2, 2)
        rho = rng.uniform(-0.999, 0.999)
        ref = stats.multivariate_normal.cdf([h, k], mean=[0, 0], cov=[[1, rho], [rho, 1]])
        assert abs(float(g.bvn_cdf(h, k, rho)) - ref) < 1e-12
    for h, k, rho in [(0, 1, 0.5), (1, 0, 0.5), (0, 0, 0.5), (0, -1, 0.7), (-1, 0, -0.7),
                      (0, 0, -0.3), (2, 2, 0.99), (-2, 1, 0.999), (1, 2, 0)]:
        ref = stats.multivariate_normal.cdf([h, k], mean=[0, 0], cov=[[1, rho], [rho, 1]])
        assert abs(float(g.bvn_cdf(h, k, rho)) - ref) < 1e-12
    # singular and infinite limits (scipy refuses the singular covariance)
    assert g.bvn_cdf(0.3, -0.2, 1.0) == pytest.approx(stats.norm.cdf(-0.2))
    anti = max(0.0, stats.norm.cdf(0.3) + stats.norm.cdf(-0.2) - 1)
    assert g.bvn_cdf(0.3, -0.2, -1.0) == pytest.approx(anti)
    assert g.bvn_cdf(0.3, np.inf, 0.4) == pytest.approx(stats.norm.cdf(0.3))
    assert g.bvn_cdf(-np.inf, 0.3, 0.4) == 0.0
    # vectorised over broadcast inputs
    out = g.bvn_cdf(np.linspace(-2, 2, 5)[:, None], 0.5, np.array([0.1, 0.9])[None, :])
    assert out.shape == (5, 2) and np.all((out >= 0) & (out <= 1))


def test_quad_closed_form_vs_numerical_integration():
    """EVSI = L (1 - (1 - R^2)^(k/2)) with L = c_k sigma0^k the MINIMAL expected
    loss under the prior (eq. lossfamily): the optimal action shifts by the
    same multiple of sigma before and after the measurement, so the identity
    is exact for asymmetric costs too, and min_expected_loss (the fit's L,
    from L1m = c_- sigma0^k, L1p = c_+ sigma0^k) equals the independent
    quadrature-plus-minimiser reference."""
    for k in (0.7, 1.0, 2.0, 3.5):
        for c_minus, c_plus in ((1.0, 1.0), (3.0, 0.5), (100.0, 1.0)):
            sigma0 = 1.7
            L, shift = min_loss(sigma0, k, c_minus, c_plus)
            fit_L, fit_shift = g.min_expected_loss(k, c_minus * sigma0**k, c_plus * sigma0**k)
            assert fit_L == pytest.approx(L, rel=1e-7) and fit_shift == pytest.approx(shift, abs=1e-5)
            for R2 in (0.1, 0.6, 0.95):
                after, shift1 = min_loss(sigma0 * np.sqrt(1 - R2), k, c_minus, c_plus)
                assert shift1 == pytest.approx(shift, abs=1e-5)           # the shift is scale-free
                evsi, evpi = g.voi_quad(L, R2, k)
                assert float(evsi) == pytest.approx(L - after, rel=1e-7)
                assert float(evpi) == pytest.approx(L)
    # E|z|^k against direct integration
    def abs_pow(z, k):
        return abs(z) ** k * stats.norm.pdf(z)

    for k in (0.5, 1.0, 2.0, 3.5, 4.0):
        mom = integrate.quad(abs_pow, -np.inf, np.inf, args=(k,))[0]
        assert float(g.abs_moment(k)) == pytest.approx(mom, rel=1e-9)


def test_partial_moment_and_minimal_loss():
    """M_k(delta) = E[(z - delta)^+^k] by the parabolic cylinder function against
    quadrature; the minimal loss reduces to the act-at-the-mean loss only for
    symmetric costs, is below it otherwise, and at k = 1 the optimal shift is
    the newsvendor quantile Phi^-1(c_- / (c_- + c_+))."""
    def m_quad(k, delta):
        return integrate.quad(lambda z: (z - delta) ** k * stats.norm.pdf(z), delta, np.inf,
                              epsabs=0, epsrel=1e-13)[0]

    for k in (0.5, 0.7, 1.0, 2.0, 3.0, 4.0):
        for delta in np.linspace(-6, 5, 23):
            ref = m_quad(k, delta)
            if ref > 1e-10:
                assert float(g.partial_moment(k, delta)) == pytest.approx(ref, rel=1e-8)
        assert float(g.partial_moment(k, 0.0)) == pytest.approx(0.5 * float(g.abs_moment(k)), rel=1e-12)
        L, shift = g.min_expected_loss(k, 7.0, 7.0)
        assert shift == pytest.approx(0.0, abs=1e-6)
        assert L == pytest.approx(7.0 * float(g.abs_moment(k)), rel=1e-12)
        L_asym, shift_asym = g.min_expected_loss(k, 7.0, 1.0)
        assert shift_asym > 0.3                                  # under-response costlier: act higher
        assert L_asym < 4.0 * float(g.abs_moment(k))             # and below the act-at-the-mean loss
        assert g.min_expected_loss(k, 1.0, 7.0)[1] == pytest.approx(-shift_asym, abs=1e-6)
    assert g.partial_moment(np.array([0.5, 4.0]), np.array([[-3.0], [12.0]])).shape == (2, 2)
    assert np.all(np.isfinite(g.partial_moment(4.0, np.array([-g.LOSS_SHIFT_BOUND, g.LOSS_SHIFT_BOUND]))))
    for cm, cp in ((3.0, 1.0), (100.0, 1.0), (1.0, 9.0)):
        assert g.min_expected_loss(1.0, cm, cp)[1] == pytest.approx(stats.norm.ppf(cm / (cm + cp)), abs=1e-6)
    # the anchors of the Gaussian template (independent reference: quad + minimiser)
    assert g.min_expected_loss(2.0, 30000.0, 4000.0)[0] == pytest.approx(9567.35, rel=1e-5)
    assert g.min_expected_loss(2.0, 120.0, 40.0)[0] == pytest.approx(66.504, rel=1e-4)


def test_kg_matches_monte_carlo_of_the_preposterior_mean():
    """eq. kg: kappa (E[(mu1 - theta_c)^+] - (mu0 - theta_c)^+), mu1 ~ N(mu0, sigtilde^2)."""
    rng = np.random.default_rng(0)
    n = 2_000_000
    z = rng.standard_normal(n)
    for R2 in (0.3, 0.9, 1.0):
        for d in (-2.0, -0.5, 0.0, 1.0):
            kappa_sigma0 = 3.0
            mu1 = d + np.sqrt(R2) * z          # (mu1 - theta_c) / sigma0
            samples = kappa_sigma0 * (np.maximum(mu1, 0.0) - max(d, 0.0))
            mc, se = samples.mean(), samples.std() / np.sqrt(n)
            closed = float(g.voi_kg(kappa_sigma0, d, R2)[0])
            assert abs(closed - mc) < 6 * se + 1e-12


def test_kg_limits_and_identities():
    d = np.linspace(-6, 6, 121)
    assert np.allclose(g.voi_kg(2.0, d, 1.0)[0], 2.0 * g.psi(d))       # EVSI = EVPI at R^2 = 1
    assert np.allclose(g.voi_kg(2.0, d, 0.5)[1], 2.0 * g.psi(d))       # EVPI = kappa sigma0 Psi(d)
    for big in (8.0, -8.0, 30.0):
        assert float(g.voi_kg(1.0, big, 0.5)[0]) < 1e-12               # -> 0 for |d| large
    assert float(g.voi_kg(1.0, 0.0, 0.0)[0]) == 0.0                     # no information at R = 0
    assert float(g.psi(0.0)) == pytest.approx(1 / np.sqrt(2 * np.pi))
    assert np.allclose(g.psi(d), g.psi(-d))                             # even
    evsi, evpi = g.voi_kg(1.0, d, 0.4)
    assert np.all(evsi >= 0) and np.all(evsi <= evpi + 1e-15)


def test_step_matches_brute_force_integration_over_y():
    """The stored EVSI_step (exact cutoff route) reproduces the integral over
    y and the posterior to 1e-8 Lambda, including at the d where the
    quadrature peaks; the design's 64-node Gauss-Hermite quadrature agrees
    only where the sensor is coarse and misses 1.8e-3 / 1.6e-2 / 4.3e-2 Lambda
    at R^2 = 0.9 / 0.99 / 0.999 (the numbers the docs quote; measured against
    the exact route on a 0.01 grid in d, since the error is spiky in d and a
    coarse grid understates it)."""
    worst_exact = 0.0
    for R2 in (0.05, 0.3, 0.6, 0.9, 0.99, 0.999):
        for d in list(np.linspace(-4, 4, 33)) + [0.10, -0.65]:
            ref = step_bruteforce(d, R2, B, K)
            worst_exact = max(worst_exact, abs(float(g.voi_step(d, R2, B, K)[0]) - ref) / LAMBDA)
    assert worst_exact < 1e-8
    d = np.arange(-4.0, 4.0 + 1e-9, 0.01)
    worst_gh = {R2: float(np.max(np.abs(g.voi_step_gh(d, R2, B, K)[0] - g.voi_step(d, R2, B, K)[0])) / LAMBDA)
                for R2 in (0.3, 0.9, 0.99, 0.999)}
    assert worst_gh[0.3] < 1e-3                                # the quadrature is fine for coarse sensors
    assert 1.5e-3 < worst_gh[0.9] < 2e-3
    assert 1.5e-2 < worst_gh[0.99] < 1.7e-2
    assert 4e-2 < worst_gh[0.999] < 4.5e-2                     # almost all of the value near d = -0.6


def test_stepfix_equals_binary_model_at_derived_st():
    d = np.linspace(-4, 4, 41)[:, None]
    R2 = np.array([0.05, 0.5, 0.95])[None, :]
    evsi, evpi, s, t = g.voi_stepfix(d, R2, B, K)
    ref_evsi, ref_evpi = model.voi(stats.norm.cdf(d), s, t, B, K)
    assert evsi.shape == s.shape == (41, 3)
    assert np.array_equal(evsi, ref_evsi) and np.allclose(evpi, ref_evpi)
    assert np.allclose(evpi, np.minimum(stats.norm.cdf(d) * B, (1 - stats.norm.cdf(d)) * K))
    # the derived s against a double integral of the bivariate density
    dd, rr = -1.4, 0.81
    R = np.sqrt(rr)
    f = lambda w, u: stats.multivariate_normal.pdf([u, w], mean=[0, 0], cov=[[1, R], [R, 1]])  # noqa: E731
    num = integrate.dblquad(f, -dd, 8, lambda u: -dd * R, lambda u: 8)[0]
    assert float(g.derived_st(dd, rr)[0]) == pytest.approx(num / stats.norm.cdf(dd), rel=1e-8)
    num_t = integrate.dblquad(f, -8, -dd, lambda u: -8, lambda u: -dd * R)[0]
    assert float(g.derived_st(dd, rr)[1]) == pytest.approx(num_t / stats.norm.cdf(-dd), rel=1e-8)
    # far in the tail Owen's T route cancels to nothing (s = 0.045 instead of 0.522 at
    # R^2 = 0.2, d = -9; 0.000 at 0.5, -12); the stored s, t come from the 1-D tail integral
    for R2, d in ((0.2, -9.0), (0.5, -12.0), (0.05, -8.0), (0.9, -15.5), (0.2, -7.0)):
        c = -d * np.sqrt(R2)
        s, t = g.derived_st(d, R2)
        assert float(s) == pytest.approx(s_tail_reference(d, R2, c), abs=1e-9)
        assert float(t) == pytest.approx(s_tail_reference(-d, R2, -c), abs=1e-9)   # t(d, c) = s(-d, -c)
        s2, t2 = g.derived_st(-d, R2)                                              # the mirror
        assert float(t2) == pytest.approx(float(s), abs=1e-12)
        assert float(s2) == pytest.approx(float(t), abs=1e-12)
        assert float(g.voi_stepfix(d, R2, B, K)[0]) == 0.0 and float(g.voi_step(d, R2, B, K)[0]) == 0.0
    assert float(g.derived_st(-9.0, 0.2)[0]) == pytest.approx(0.5216, abs=5e-4)
    assert float(g.derived_st(-12.0, 0.5)[0]) == pytest.approx(0.5326, abs=5e-4)
    # the two routes agree at the switch, and the vectorised call matches scalar calls
    for R2 in (0.05, 0.5):
        lo, hi = g.derived_st(-g.TAIL_D - 1e-9, R2), g.derived_st(-g.TAIL_D + 1e-9, R2)
        assert float(lo[0]) == pytest.approx(float(hi[0]), abs=1e-8)
    dv = np.array([-1.4, -9.0, 0.3, 8.0, -9.0, np.inf, -np.inf])
    sv, tv = g.derived_st(dv, 0.2)
    for i, di in enumerate(dv):
        si, ti = g.derived_st(di, 0.2)
        assert float(sv[i]) == float(si) and float(tv[i]) == float(ti)
    assert sv.shape == (7,) and np.all(sv + tv >= 1.0)


def test_derived_s_plus_t_exceeds_one_whenever_R_positive():
    d = np.linspace(-5, 5, 101)[:, None]
    R2 = np.array([1e-4, 0.01, 0.2, 0.5, 0.8, 0.99])[None, :]
    s, t = g.derived_st(d, R2)
    assert np.all(s + t > 1.0)
    s1, t1 = g.derived_st(d, 1.0)
    assert np.allclose(s1, 1.0) and np.allclose(t1, 1.0)         # a perfect sensor
    s0, t0 = g.derived_st(d, 0.0)
    assert np.allclose(s0 + t0, 1.0)                              # an uninformative one


def test_blackwell_step_dominates_stepfix_on_a_grid():
    d = np.linspace(-5, 5, 201)[:, None]
    R2 = np.array([0.01, 0.1, 0.5, 0.9, 0.99, 1.0])[None, :]
    ev_step, evpi = g.voi_step(d, R2, B, K)
    ev_fix, evpi_f, _, _ = g.voi_stepfix(d, R2, B, K)
    assert np.array_equal(evpi, evpi_f)
    assert np.all(ev_step >= ev_fix - 1e-9 * LAMBDA)
    assert np.all(ev_step <= evpi + 1e-9 * LAMBDA) and np.all(ev_fix >= 0.0)
    assert np.allclose(ev_step[:, -1], evpi[:, -1])               # R^2 = 1: EVSI = EVPI
    assert np.all(ev_step[:, 0] < 0.05 * LAMBDA)                  # R^2 = 0.01: almost nothing
    near = np.abs(d[:, 0]) <= 3.0
    assert np.all(ev_step[near, 2] > 0.0)                         # continuous signal: no gate
    assert np.any(ev_fix[near, 2] == 0.0)                         # fixed mark: the gate reappears


def test_scenario_metrics_names_and_bias():
    n = 5
    draws = {"g_d": np.full(n, -1.4), "g_x": np.full(n, 0.4), "g_k": np.full(n, 2.0),
             "g_L": np.full(n, 17e3), "g_kappa_sigma0": np.full(n, 150e3), "g_B": np.full(n, B),
             "g_K": np.full(n, K), "g_sigma_b_rel": np.zeros(n), "C": np.full(n, 1e3)}
    assert set(draws) == set(g.METRIC_INPUTS)                       # the keys the metrics read
    assert set(g.METRIC_INPUTS) == set(GAUSS_PARAM_NAMES) - {"g_mu0", "g_sigma0"}
    m = g.scenario_metrics(draws)
    assert list(m) == g.METRIC_NAMES and all(v.shape == (n,) for v in m.values())
    assert np.allclose(m["R2"], 1 / (1 + 0.4**2)) and np.allclose(m["p_derived"], stats.norm.cdf(-1.4))
    assert np.allclose(m["EVSI_quad"], 17e3 * m["R2"]) and np.allclose(m["EVPI_quad"], 17e3)
    assert np.allclose(m["eff_step"], m["EVSI_step"] / 1e3)
    # a common-mode bias acts as extra sensor variance: r -> r + sigma_b^2 (1 - 2/pi)
    draws["g_sigma_b_rel"] = np.full(n, 0.3)
    mb = g.scenario_metrics(draws)
    assert np.allclose(mb["R2"], 1 / (1 + 0.4**2 + 0.3**2 * (1 - 2 / np.pi)))
    assert np.all(mb["EVSI_step"] < m["EVSI_step"]) and np.all(mb["EVSI_kg"] < m["EVSI_kg"])


# --- the over-determined fit --------------------------------------------------

def anchor_payload():
    """Anchor A1 of the Gaussian template: consistent by construction."""
    return {
        "state": {"reasoning": "r", "variable": "bearing-fault vibration severity", "unit": "mm/s",
                  "bad_is_high": True},
        "answers": {
            "theta": {"reasoning": "r", "p5": 1.5, "p50": 3.1, "p95": 4.8},
            "theta_c": {"reasoning": "r", "value": 4.5},
            "p_above": {"reasoning": "r", "value": 0.08},
            "W_rr": {"reasoning": "r", "value": 0.95},
            "W1": {"reasoning": "r", "value": 1.25},
            "c_move": {"reasoning": "r", "value": 0.38},
            "loss": {"reasoning": "r", "L1m": 30000, "L2m": 120000, "L1p": 4000, "L2p": 16000},
            "kappa_sigma0": {"reasoning": "r", "value": 150000},
            "B": {"reasoning": "r", "value": 150000},
            "K": {"reasoning": "r", "value": 10000},
            "sigma_b": {"reasoning": "r", "value": 0.3},
            "C": {"reasoning": "r", "p5": 300, "p50": 1000, "p95": 5000},
        },
    }


def anchor_a2_payload():
    """Anchor A2 of the Gaussian template (rapid strep test)."""
    return {
        "state": {"reasoning": "r", "variable": "group A streptococcal load", "unit": "log10 copies",
                  "bad_is_high": True},
        "answers": {
            "theta": {"reasoning": "r", "p5": 0.0, "p50": 2.4, "p95": 5.0},
            "theta_c": {"reasoning": "r", "value": 4.0},
            "p_above": {"reasoning": "r", "value": 0.15},
            "W_rr": {"reasoning": "r", "value": 1.25},
            "W1": {"reasoning": "r", "value": 1.65},
            "c_move": {"reasoning": "r", "value": 0.38},
            "loss": {"reasoning": "r", "L1m": 120, "L2m": 480, "L1p": 40, "L2p": 160},
            "kappa_sigma0": {"reasoning": "r", "value": 300},
            "B": {"reasoning": "r", "value": 300},
            "K": {"reasoning": "r", "value": 100},
            "sigma_b": {"reasoning": "r", "value": 0.3},
            "C": {"reasoning": "r", "p5": 5, "p50": 15, "p95": 50},
        },
    }


def set_in(payload, path, value):
    out = copy.deepcopy(payload)
    node = out
    for key in path[:-1]:
        node = node[key]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return out


def derive(payload):
    clean, err = gauss_fit.validate_gauss_payload(payload)
    assert err is None, err
    return gauss_fit.derive(clean)


def test_fit_on_consistent_answers_has_small_residuals_and_no_warnings():
    der = derive(anchor_payload())
    v, res, warn = der["values"], der["residuals"], der["warnings"]
    assert v["g_mu0"] == 3.1 and v["g_sigma0"] == pytest.approx(3.3 / g.W90)
    assert v["g_d"] == pytest.approx(-1.40, abs=0.01)
    assert stats.norm.cdf(v["g_d"]) == pytest.approx(0.08, abs=0.002)   # p = Phi(d) is the anchor p
    assert v["g_x"] == pytest.approx(0.40, abs=0.01) and set(der["routes"]) == {"a", "b", "c"}
    assert v["g_x"] == pytest.approx(float(np.exp(np.median(list(der["routes"].values())))))
    assert v["g_k"] == 2.0 and v["g_L"] == pytest.approx(min_loss(1.0, 2.0, 30000, 4000)[0], rel=1e-7)
    assert v["g_L"] < 0.5 * (30000 + 4000) and der["shift"] == pytest.approx(0.792, abs=0.001)
    assert v["g_sigma_b_rel"] == pytest.approx(0.3 / v["g_sigma0"])
    assert res["g_x"] < 0.05 and res["g_d"] < 0.01 and res["g_k"] == 0.0 and res["g_mu0"] < 0.05
    assert not any(warn.values()) and der["notes"] == {"g_x": [], "g_k": []}
    assert abs(der["p_mismatch"]) < 0.002
    rows, fits, err = gauss_fit.fit_gauss(gauss_fit.validate_gauss_payload(anchor_payload())[0])
    assert err is None and list(rows) == GAUSS_PARAM_NAMES and list(fits) == GAUSS_PARAM_NAMES
    for name in GAUSS_PARAM_NAMES:
        if name == "C":
            assert fits[name].family == "lognormal" and rows[name]["p5"] == 300
        else:
            assert fits[name].family == "point" and fits[name].params == {"value": v[name]}
            assert rows[name]["p5"] == rows[name]["p50"] == rows[name]["p95"] == v[name]
    assert rows["g_mu0"]["unit"] == "mm/s" and rows["g_d"]["unit"] == "dimensionless"
    assert rows["g_L"]["unit"] == "USD" and "state: bearing-fault" in rows["g_sigma0"]["reasoning"]
    assert rows["g_L"]["reasoning"].startswith("optimal action shift +0.79 sigma0 | loss:")
    assert rows["g_d"]["reasoning"].startswith("Q2b - Phi(d from Q2a) ")
    assert "| theta_c:" in rows["g_d"]["reasoning"]
    assert gauss_fit.consistency_score({n: fits[n].residual for n in fits if n != "C"}) < 0.25


def test_fit_residuals_and_warnings_on_inconsistent_answers():
    base = anchor_payload()
    # Q1 asymmetric triple
    der = derive(set_in(base, ("answers", "theta", "p50"), 2.0))
    assert der["residuals"]["g_mu0"] == pytest.approx(abs(2.8 - 0.5) / 3.3)
    assert der["warnings"]["g_mu0"] and der["warnings"]["g_sigma0"]
    # Q2b disagrees with the triple and theta_c: d is the mean of the two implied d's and the
    # residual is their distance in prior-sd units
    der = derive(set_in(base, ("answers", "p_above", "value"), 0.40))
    d_a = (3.1 - 4.5) / (3.3 / g.W90)
    assert der["residuals"]["g_d"] == pytest.approx(abs(d_a - stats.norm.ppf(0.40)))
    assert der["values"]["g_d"] == pytest.approx(0.5 * (d_a + stats.norm.ppf(0.40)))
    assert der["warnings"]["g_d"] and der["p_mismatch"] == pytest.approx(0.40 - stats.norm.cdf(d_a))
    # Q3 routes disagree: x is the median of the three log routes, so the outlier route a
    # does not move it; the std of the logs is the residual
    der = derive(set_in(base, ("answers", "W_rr", "value"), 3.0))
    assert der["residuals"]["g_x"] > 0.5 and der["warnings"]["g_x"]
    logs = sorted(der["routes"].values())
    assert der["values"]["g_x"] == pytest.approx(float(np.exp(logs[1])))
    assert der["values"]["g_x"] == pytest.approx(0.40, abs=0.02)        # not exp(mean) = 0.6
    assert der["residuals"]["g_x"] == pytest.approx(float(np.std(logs)))
    # Q3c beyond what a Gaussian sensor can do: the route is dropped with a warning; the
    # drop point is 0.40 (0.4108 is the bound, and the last 0.01 no longer resolves x)
    der = derive(set_in(base, ("answers", "c_move", "value"), 0.6))
    assert set(der["routes"]) == {"a", "b"} and der["warnings"]["g_x"]
    assert any("Q3c dropped" in n and "0.4108" in n for n in der["notes"]["g_x"])
    assert der["notes"]["g_k"] == []                    # a sensor note is not a loss note
    rows, _, _ = gauss_fit.fit_gauss(gauss_fit.validate_gauss_payload(
        set_in(base, ("answers", "c_move", "value"), 0.6))[0])
    assert rows["g_x"]["reasoning"].startswith("Q3c dropped")
    assert "Q3c dropped" not in rows["g_k"]["reasoning"]
    assert rows["g_k"]["reasoning"].startswith("loss:")
    assert der["values"]["g_x"] == pytest.approx(float(np.exp(np.mean(list(der["routes"].values())))))
    assert gauss_fit.C_MOVE_MAX == pytest.approx(2 * (1 - stats.norm.cdf(g.Z95 / 2)))
    assert "c" not in gauss_fit.x_routes(1.0, 0.95, 1.25, 0.405)
    assert "c" not in gauss_fit.x_routes(1.0, 0.95, 1.25, 0.41)
    routes = gauss_fit.x_routes(1.0, 0.95, 1.25, 0.40)
    assert "c" in routes and np.exp(routes["c"]) == pytest.approx(0.22, abs=0.01)
    # a coarse c at the drop point cannot drag x: the median keeps the two agreeing routes
    der = derive(set_in(base, ("answers", "c_move", "value"), 0.40))
    assert der["values"]["g_x"] == pytest.approx(0.40, abs=0.01)
    # Q4: the two sides disagree on the exponent; k is their mean
    der = derive(set_in(base, ("answers", "loss", "L2p"), 64000))
    assert der["values"]["g_k"] == 3.0 and der["residuals"]["g_k"] == 2.0
    assert der["warnings"]["g_k"] and der["warnings"]["g_L"]
    # k clipped to [0.5, 4]
    clipped = set_in(set_in(base, ("answers", "loss", "L2m"), 30000), ("answers", "loss", "L2p"), 4000)
    der = derive(clipped)
    assert der["values"]["g_k"] == 0.5 and any("clipped" in n for n in der["notes"]["g_k"])
    assert der["notes"]["g_x"] == []
    rows, _, _ = gauss_fit.fit_gauss(gauss_fit.validate_gauss_payload(clipped)[0])
    assert rows["g_k"]["reasoning"].startswith("k clipped from 0 to 0.5 | loss:")
    assert "clipped" not in rows["g_x"]["reasoning"]
    der = derive(set_in(set_in(base, ("answers", "loss", "L2m"), 3e6), ("answers", "loss", "L2p"), 4e5))
    assert der["values"]["g_k"] == 4.0
    # the warning lands on the stored rows
    rows, fits, err = gauss_fit.fit_gauss(
        gauss_fit.validate_gauss_payload(set_in(base, ("answers", "loss", "L2p"), 64000))[0])
    assert err is None and fits["g_k"].warning and fits["g_L"].warning and not fits["g_d"].warning
    assert fits["g_k"].residual == 2.0 and "loss:" in rows["g_k"]["reasoning"]


def test_d_mismatch_is_measured_in_sd_units_not_probability():
    """Q2b = 0.05 (d_b = -1.64) against a theta_c six sd above the estimate (d_a = -6,
    Phi = 1e-9): in probability the answers differ by 0.050, under the old 0.15
    threshold no warning, while the pooled d = -3.82 gives an EVSI_step orders of
    magnitude away from either answer's. In sd units the residual is 4.4."""
    base = anchor_payload()
    sigma0 = 3.3 / g.W90
    far = set_in(set_in(base, ("answers", "theta_c", "value"), 3.1 + 6.0 * sigma0),
                 ("answers", "p_above", "value"), 0.05)
    der = derive(far)
    d_a, d_b = -6.0, stats.norm.ppf(0.05)
    assert der["residuals"]["g_d"] == pytest.approx(abs(d_a - d_b), abs=1e-9)
    assert der["residuals"]["g_d"] > 4.0 and der["warnings"]["g_d"]
    assert abs(der["p_mismatch"]) == pytest.approx(0.05, abs=1e-6)     # what the old residual saw
    assert der["values"]["g_d"] == pytest.approx(0.5 * (d_a + d_b))
    evsi_at = lambda d: float(g.voi_step(d, 0.83, 150e3, 10e3)[0])  # noqa: E731
    assert evsi_at(d_b) > 1e3 * evsi_at(der["values"]["g_d"]) > 1e3 * evsi_at(d_a)
    assert gauss_fit.THRESHOLDS["g_d"] == 0.5
    # a half-sd disagreement is the threshold; a quarter is not flagged
    for delta, flagged in ((0.25, False), (0.6, True)):
        q = float(stats.norm.cdf(-1.4 + delta))
        der = derive(set_in(set_in(base, ("answers", "theta_c", "value"), 3.1 + 1.4 * sigma0),
                            ("answers", "p_above", "value"), q))
        assert der["residuals"]["g_d"] == pytest.approx(delta, abs=1e-9) and der["warnings"]["g_d"] == flagged
    rows, fits, err = gauss_fit.fit_gauss(gauss_fit.validate_gauss_payload(far)[0])
    assert err is None and fits["g_d"].warning and fits["g_d"].residual > 4.0
    assert rows["g_d"]["reasoning"].startswith("Q2b - Phi(d from Q2a) +0.050 |")
    assert gauss_fit.consistency_score({"g_d": 1.0, "g_x": 0.1, "g_k": 0.0, "g_sigma0": 0.0}) == 2.0


@pytest.mark.parametrize("study", ("business", "ai-safety-evals", "sim2real"))
def test_template_implied_lines_quote_the_fitters_numbers(study):
    """The anchors' Implied lines state what gauss_fit.derive returns from the
    listed answers (x, R^2 before and after the sigma_b correction, d, k, L,
    the shift, s and t at the corrected R^2), not the design values the
    answers were solved from."""
    text = (STUDY_DIRS[study] / "templates" / "elicitor_gauss.md").read_text()
    implied = re.findall(r"^- Implied: (.*)$", text, flags=re.M)
    assert len(implied) == 2
    anchors = ((implied[0], anchor_payload(), 0.08), (implied[1], anchor_a2_payload(), 0.15))
    for line, payload, p_binary in anchors:
        der = derive(payload)
        v = der["values"]
        x, sb = v["g_x"], v["g_sigma_b_rel"]
        r2_raw, r2_eff = 1.0 / (1.0 + x**2), float(g.r2_effective(x, sb))
        s, t = g.derived_st(v["g_d"], r2_eff)
        assert f"x = {x:.2f} (R^2 = {r2_raw:.2f} before, {r2_eff:.2f} after the sigma_b correction)" in line
        assert r2_eff < r2_raw - 0.005                      # the correction is visible at two decimals
        assert f"d = {v['g_d']:.2f}" in line and f"k = {v['g_k']:g}" in line
        assert f"sensitivity {float(s):.2f} and specificity {float(t):.2f} (at the corrected R^2)" in line
        assert f"{der['shift']:.2f} sigma0 above the estimate" in line
        assert f"mu0 = {v['g_mu0']:g}, sigma0 = {v['g_sigma0']:.1f}" in line
        assert stats.norm.cdf(v["g_d"]) == pytest.approx(p_binary, abs=0.003)
        assert not any(der["warnings"].values())
    assert "L = 9,570 USD" in implied[0]
    assert derive(anchor_payload())["values"]["g_L"] == pytest.approx(9567.35, abs=0.01)
    assert "L = 66.5 USD" in implied[1]
    assert derive(anchor_a2_payload())["values"]["g_L"] == pytest.approx(66.50, abs=0.01)
    # Q3b and Q3c ask for the random error alone, so sigma_b is not counted twice
    assert "counting the random error of the result only" in text
    assert "three routes to the same random error; leave the systematic error out of all three" in text


@pytest.mark.parametrize("path, value, expect", [
    (("state",), KeyError, "schema: missing 'state' object"),
    (("answers",), KeyError, "schema: missing 'answers' object"),
    (("state", "variable"), "  ", "schema: state.variable must be a non-empty string"),
    (("state", "unit"), KeyError, "schema: state.unit must be a non-empty string"),
    (("state", "bad_is_high"), False, "schema: state.bad_is_high must be true"),
    (("state", "bad_is_high"), "true", "schema: state.bad_is_high must be true"),
    (("answers", "W1"), KeyError, "schema: missing answers ['W1']"),
    (("answers", "theta"), [1, 2, 3], "schema: theta is not an object"),
    (("answers", "theta", "p50"), "abc", "schema: theta: missing or non-numeric percentiles"),
    (("answers", "loss", "L2p"), KeyError, "schema: loss: missing or non-numeric L1m/L2m/L1p/L2p"),
    (("answers", "B", "value"), None, "schema: B: missing or non-numeric value"),
    (("answers", "theta", "p50"), 5.0, "constraint: theta: percentiles not strictly increasing"),
    (("answers", "p_above", "value"), 0.0, "constraint: p_above: must lie in (0.001, 0.999)"),
    (("answers", "p_above", "value"), 1.0, "constraint: p_above: must lie in (0.001, 0.999)"),
    (("answers", "W_rr", "value"), 0.0, "constraint: W_rr: must be > 0"),
    (("answers", "W1", "value"), -1.0, "constraint: W1: must be > 0"),
    (("answers", "W1", "value"), 3.3, "constraint: W1: the 90% interval after the result must be narrower"),
    (("answers", "c_move", "value"), 0.9995, "constraint: c_move: must lie in (0.001, 0.999)"),
    (("answers", "loss", "L1m"), -5.0, "constraint: loss: L1m, L2m, L1p, L2p must be > 0"),
    (("answers", "loss", "L2m"), 1000.0, "constraint: loss: L2m >= L1m and L2p >= L1p"),
    (("answers", "kappa_sigma0", "value"), 0.0, "constraint: kappa_sigma0: must be > 0"),
    (("answers", "K", "value"), -1.0, "constraint: K: must be > 0"),
    (("answers", "sigma_b", "value"), -0.1, "constraint: sigma_b: must be >= 0"),
    (("answers", "C", "p95"), 500.0, "constraint: C: percentiles not strictly increasing"),
    (("answers", "C", "p5"), 0.0, "constraint: C: must be > 0"),
])
def test_validation_rejects_each_malformed_shape(path, value, expect):
    clean, err = gauss_fit.validate_gauss_payload(set_in(anchor_payload(), path, value))
    assert clean is None and err.startswith(expect), err
    assert err.split(":", 1)[0] in ("schema", "constraint")   # what health.error_class classifies


def test_validation_accepts_extra_keys_and_parse_helper():
    payload = set_in(anchor_payload(), ("answers", "extra"), {"value": 1})
    clean, err = gauss_fit.validate_gauss_payload(payload)
    assert err is None and "extra" not in clean
    assert gauss_fit.validate_gauss_payload("not a dict")[1] == "schema: missing 'state' object"
    assert gauss_fit.parse_gauss("{not json")[2].startswith("json:")
    import json
    rows, fits, err = gauss_fit.parse_gauss(json.dumps(anchor_payload()))
    assert err is None and rows["g_d"]["p50"] == fits["g_d"].params["value"]


def test_step_fence_is_the_maximum_of_the_step_value_over_d():
    """voi_step_fence evaluates the continuous-signal step model at d* =
    Phi^-1(K / (B + K)), where the prior sits on the fence; that is the
    maximum of EVSI_step over d (the state threshold), on a fine grid."""
    d = np.linspace(-4.0, 4.0, 4001)
    for R2, B, K in ((0.3, 1e6, 1e5), (0.83, 150e3, 10e3), (0.95, 2e4, 3e4), (0.5, 1.0, 1.0)):
        fence, evpi = g.voi_step_fence(R2, B, K)
        d_star = float(stats.norm.ppf(K / (B + K)))
        assert float(fence) == pytest.approx(float(g.voi_step(d_star, R2, B, K)[0]), rel=1e-12)
        grid = g.voi_step(d, R2, B, K)[0]
        assert float(np.max(grid)) <= float(fence) * (1 + 1e-9)
        for h in (1e-4, 1e-2, 0.3):   # a kinked maximum: strictly lower on either side
            assert float(g.voi_step(d_star - h, R2, B, K)[0]) < float(fence)
            assert float(g.voi_step(d_star + h, R2, B, K)[0]) < float(fence)
        assert abs(float(d[np.argmax(grid)]) - d_star) <= 0.01
        assert float(evpi) == pytest.approx(B * K / (B + K))   # min(pB, (1 - p)K) at p = pi*
