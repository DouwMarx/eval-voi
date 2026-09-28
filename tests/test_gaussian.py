"""Gaussian-state family (spec v2.1): closed forms against numerical
integration, the action-model identities of the chapter, the over-determined
fit with its residuals and warnings, and the payload validation."""

import copy

import numpy as np
import pytest
from scipy import integrate, stats

from voi_rank import gauss_fit, model
from voi_rank import gaussian as g
from voi_rank.fit import GAUSS_PARAM_NAMES

B, K = 150e3, 10e3
LAMBDA = B + K


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


def act_at_mean_loss(sigma, k, c_minus, c_plus):
    """Expected loss of acting at the mean of a N(., sigma^2) belief under the
    loss c_- |a - theta|^k (a < theta) / c_+ |a - theta|^k (a > theta)."""
    f = lambda z: (c_plus if z < 0 else c_minus) * abs(sigma * z) ** k * stats.norm.pdf(z)  # noqa: E731
    return integrate.quad(f, -np.inf, 0)[0] + integrate.quad(f, 0, np.inf)[0]


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
    """EVSI = L (1 - (1 - R^2)^(k/2)) with L the expected loss of acting at
    the prior mean (eq. lossfamily), for symmetric and asymmetric costs."""
    for k in (0.7, 1.0, 2.0, 3.5):
        for c_minus, c_plus in ((1.0, 1.0), (3.0, 0.5)):
            for R2 in (0.1, 0.6, 0.95):
                sigma0 = 1.7
                L = act_at_mean_loss(sigma0, k, c_minus, c_plus)
                after = act_at_mean_loss(sigma0 * np.sqrt(1 - R2), k, c_minus, c_plus)
                evsi, evpi = g.voi_quad(L, R2, k)
                assert float(evsi) == pytest.approx(L - after, rel=1e-8)
                assert float(evpi) == pytest.approx(L)
    # E|z|^k against direct integration (used by the fit for L)
    def abs_pow(z, k):
        return abs(z) ** k * stats.norm.pdf(z)

    for k in (0.5, 1.0, 2.0, 3.5, 4.0):
        mom = integrate.quad(abs_pow, -np.inf, np.inf, args=(k,))[0]
        assert float(g.abs_moment(k)) == pytest.approx(mom, rel=1e-9)


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
    y and the posterior to 1e-8 Lambda; the design's 64-node Gauss-Hermite
    quadrature agrees only where the sensor is coarse and misses up to a few
    percent of Lambda as R^2 -> 1 (why it is not the stored metric)."""
    worst_exact, worst_gh = 0.0, {}
    for R2 in (0.05, 0.3, 0.6, 0.9, 0.99, 0.999):
        for d in np.linspace(-4, 4, 33):
            ref = step_bruteforce(d, R2, B, K)
            exact = float(g.voi_step(d, R2, B, K)[0])
            gh = float(g.voi_step_gh(d, R2, B, K)[0])
            worst_exact = max(worst_exact, abs(exact - ref) / LAMBDA)
            worst_gh[R2] = max(worst_gh.get(R2, 0.0), abs(gh - ref) / LAMBDA)
    assert worst_exact < 1e-8
    assert worst_gh[0.3] < 1e-3 and worst_gh[0.9] < 3e-3     # the quadrature is fine for coarse sensors
    assert worst_gh[0.999] > 1e-2                              # and off by > 1% of Lambda for a sharp one


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
    assert v["g_k"] == 2.0 and v["g_L"] == pytest.approx(0.5 * (30000 + 4000))
    assert v["g_sigma_b_rel"] == pytest.approx(0.3 / v["g_sigma0"])
    assert res["g_x"] < 0.05 and res["g_d"] < 0.01 and res["g_k"] == 0.0 and res["g_mu0"] < 0.05
    assert not any(warn.values()) and der["notes"] == []
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
    assert gauss_fit.consistency_score({n: fits[n].residual for n in fits if n != "C"}) < 0.25


def test_fit_residuals_and_warnings_on_inconsistent_answers():
    base = anchor_payload()
    # Q1 asymmetric triple
    der = derive(set_in(base, ("answers", "theta", "p50"), 2.0))
    assert der["residuals"]["g_mu0"] == pytest.approx(abs(2.8 - 0.5) / 3.3)
    assert der["warnings"]["g_mu0"] and der["warnings"]["g_sigma0"]
    # Q2b disagrees with the triple and theta_c: d is the mean of the two implied d's
    der = derive(set_in(base, ("answers", "p_above", "value"), 0.40))
    d_a = (3.1 - 4.5) / (3.3 / g.W90)
    assert der["residuals"]["g_d"] == pytest.approx(abs(0.40 - stats.norm.cdf(d_a)))
    assert der["values"]["g_d"] == pytest.approx(0.5 * (d_a + stats.norm.ppf(0.40)))
    assert der["warnings"]["g_d"]
    # Q3 routes disagree
    der = derive(set_in(base, ("answers", "W_rr", "value"), 3.0))
    assert der["residuals"]["g_x"] > 0.5 and der["warnings"]["g_x"]
    assert der["values"]["g_x"] == pytest.approx(float(np.exp(np.mean(list(der["routes"].values())))))
    # Q3c beyond what a Gaussian sensor can do: the route is dropped with a warning
    der = derive(set_in(base, ("answers", "c_move", "value"), 0.6))
    assert set(der["routes"]) == {"a", "b"} and der["warnings"]["g_x"]
    assert any("Q3c dropped" in n for n in der["notes"])
    # Q4: the two sides disagree on the exponent; k is their mean
    der = derive(set_in(base, ("answers", "loss", "L2p"), 64000))
    assert der["values"]["g_k"] == 3.0 and der["residuals"]["g_k"] == 2.0
    assert der["warnings"]["g_k"] and der["warnings"]["g_L"]
    # k clipped to [0.5, 4]
    der = derive(set_in(set_in(base, ("answers", "loss", "L2m"), 30000), ("answers", "loss", "L2p"), 4000))
    assert der["values"]["g_k"] == 0.5 and any("clipped" in n for n in der["notes"])
    der = derive(set_in(set_in(base, ("answers", "loss", "L2m"), 3e6), ("answers", "loss", "L2p"), 4e5))
    assert der["values"]["g_k"] == 4.0
    # the warning lands on the stored rows
    rows, fits, err = gauss_fit.fit_gauss(
        gauss_fit.validate_gauss_payload(set_in(base, ("answers", "loss", "L2p"), 64000))[0])
    assert err is None and fits["g_k"].warning and fits["g_L"].warning and not fits["g_d"].warning
    assert fits["g_k"].residual == 2.0 and "loss:" in rows["g_k"]["reasoning"]


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
