"""Percentile triples (q05, q50, q95) -> fitted distributions (spec §3).

Lognormal for B, K, C; Beta for p, s, t, e. Fits are performed once at
elicitation time and stored in the DB; never re-fit at analysis time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from scipy import optimize, stats

Z95 = float(stats.norm.ppf(0.95))
QLEVELS = np.array([0.05, 0.50, 0.95])
BETA_RESIDUAL_FLAG = 0.02       # spec §3: flag beta fits with residual > 0.02
LOGNORMAL_ASYMMETRY_FLAG = 0.25  # spec §3: flag asymmetric log-quantiles
_EPS = 1e-6

FAMILY_BY_PARAM = {
    "p": "beta", "s": "beta", "t": "beta", "e": "beta",
    "B": "lognormal", "K": "lognormal", "C": "lognormal",
}


@dataclass
class FitResult:
    family: str      # "lognormal" | "beta"
    params: dict     # {"mu", "sigma"} | {"alpha", "beta"}
    residual: float  # RMS error over the three target quantiles (log space for lognormal)
    warning: bool

    def params_json(self) -> str:
        return json.dumps(self.params)


def fit_param(name: str, q05: float, q50: float, q95: float) -> FitResult:
    family = FAMILY_BY_PARAM[name]
    if family == "lognormal":
        return fit_lognormal(q05, q50, q95)
    return fit_beta(q05, q50, q95)


def _validate(q05, q50, q95):
    if not (q05 < q50 < q95):
        raise ValueError(f"percentiles must be strictly increasing, got ({q05}, {q50}, {q95})")


def fit_lognormal(q05: float, q50: float, q95: float) -> FitResult:
    """Init mu = ln q50, sigma = (ln q95 - ln q05) / (2 * 1.6449), then
    least-squares refine against the three quantiles.

    The refinement runs on log-quantiles (the model is exactly
    ln Q(u) = mu + sigma * z_u), so the largest quantile does not dominate.
    """
    _validate(q05, q50, q95)
    if q05 <= 0:
        raise ValueError("lognormal quantiles must be > 0")
    lq = np.log([q05, q50, q95])
    z = np.array([-Z95, 0.0, Z95])
    x0 = [lq[1], max((lq[2] - lq[0]) / (2 * Z95), _EPS)]

    def resid(theta):
        return theta[0] + theta[1] * z - lq

    sol = optimize.least_squares(resid, x0=x0, bounds=([-np.inf, _EPS], [np.inf, np.inf]))
    mu, sigma = (float(v) for v in sol.x)
    residual = float(np.sqrt(np.mean(resid([mu, sigma]) ** 2)))
    asymmetry = abs((lq[2] - lq[1]) - (lq[1] - lq[0])) / (lq[2] - lq[0])
    return FitResult("lognormal", {"mu": mu, "sigma": sigma}, residual,
                     bool(asymmetry > LOGNORMAL_ASYMMETRY_FLAG))


def fit_beta(q05: float, q50: float, q95: float) -> FitResult:
    """Clip quantiles to [1e-6, 1-1e-6], init (alpha, beta) by method of moments
    with mean = q50 and sd = (q95 - q05) / 3.29 (sd clipped to the valid Beta
    range), then least-squares refine against the three quantiles."""
    _validate(q05, q50, q95)
    q = np.clip([q05, q50, q95], _EPS, 1.0 - _EPS)
    if not (q[0] < q[1] < q[2]):
        raise ValueError("percentiles collapse after clipping to (0, 1)")
    m = q[1]
    sd = (q[2] - q[0]) / 3.29
    sd = float(np.clip(sd, 1e-4, 0.99 * np.sqrt(m * (1.0 - m))))
    nu = m * (1.0 - m) / sd**2 - 1.0
    x0 = np.log([max(m * nu, 1e-3), max((1.0 - m) * nu, 1e-3)])

    def resid(log_ab):
        a, b = np.exp(log_ab)
        return stats.beta.ppf(QLEVELS, a, b) - q

    sol = optimize.least_squares(resid, x0=x0, bounds=(np.log(1e-3), np.log(1e6)))
    alpha, beta = (float(v) for v in np.exp(sol.x))
    residual = float(np.sqrt(np.mean(resid(np.log([alpha, beta])) ** 2)))
    return FitResult("beta", {"alpha": alpha, "beta": beta}, residual,
                     bool(residual > BETA_RESIDUAL_FLAG))
