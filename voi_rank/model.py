"""The decision model (DESIGN section 3): closed-form EVSI and EVPI for the
binary-state, binary-result, binary-action release decision, the maximum
EVSI over the threshold (EVSI*), and the per-draw metrics the Monte Carlo
stores. Vectorized over NumPy arrays.

Convention: theta=1 is the state in which mitigating (a=1) is the correct
action. Utilities are in the regret parameterization with u(theta, a=0) = 0,
u(1,1) = B, u(0,1) = -K. Stakes Lambda = B + K, threshold pi* = K / Lambda,
V(pi) = Lambda [pi - pi*]^+.
"""

import numpy as np

METRIC_NAMES = ["EVSI", "EVPI", "EVSI_ind", "C", "eta", "eta_ind", "eta_run", "n_star"]


def value_of_acting(pi, B, K):
    """V(pi) = max(0, pi*B - (1-pi)*K): value of acting optimally at belief pi."""
    return np.maximum(0.0, pi * B - (1.0 - pi) * K)


def voi(p, s, t, B, K):
    """Return (EVSI, EVPI), broadcasting over array inputs.

    P1 = ps + (1-p)(1-t); pi1 = ps/P1; pi0 = p(1-s)/(1-P1);
    EVSI = P1 V(pi1) + (1-P1) V(pi0) - V(p); EVPI = min(pB, (1-p)K).
    Guards: if P(x=1) or P(x=0) is zero, that branch contributes 0.
    EVSI is clipped into [0, EVPI], which holds mathematically; the clip only
    removes last-ulp floating-point noise.
    """
    p, s, t, B, K = (np.asarray(v, dtype=float) for v in (p, s, t, B, K))
    P1 = p * s + (1.0 - p) * (1.0 - t)
    P0 = 1.0 - P1
    pi1 = np.where(P1 > 0.0, p * s / np.where(P1 > 0.0, P1, 1.0), 0.0)
    pi0 = np.where(P0 > 0.0, p * (1.0 - s) / np.where(P0 > 0.0, P0, 1.0), 0.0)
    evsi = (
        P1 * value_of_acting(pi1, B, K)
        + P0 * value_of_acting(pi0, B, K)
        - value_of_acting(p, B, K)
    )
    evpi = np.minimum(p * B, (1.0 - p) * K)
    evsi = np.minimum(np.maximum(evsi, 0.0), evpi)
    # snap float-cancellation residue to an exact 0. Measured residue when the
    # true EVSI is 0 is ~1e-15 of the utility scale; 1e-13 gives two orders of
    # margin above it while staying below the 1e-12 test tolerance, and an
    # EVSI below 1e-13 of the stakes is economically zero in any case.
    noise = 1e-13 * np.maximum(B, K)
    evsi = np.where(evsi <= noise, 0.0, evsi)
    return evsi, evpi


def voi_indifference(p, s, t, B, K):
    """EVSI* = Lambda p (1 - p) (s + t - 1), Lambda = B + K: the maximum of
    EVSI over the threshold pi* = K / (B + K) at fixed stakes, reached when
    the decision maker is exactly undecided (pi* = p). Stakes times the
    Bernoulli variance of the state times Youden's index J = s + t - 1:
    smooth in every input and positive whenever the evaluation is
    informative, so it ranks evaluations whether or not the result can
    change the decision. An inverted evaluation (s + t < 1, which the
    elicitation rejects but a mixture draw can produce) is read the other
    way round, |s + t - 1|, as voi does. The code keeps the historical key
    EVSI_ind; the documents write EVSI*."""
    p, s, t, B, K = (np.asarray(v, dtype=float) for v in (p, s, t, B, K))
    return (B + K) * p * (1.0 - p) * np.abs(s + t - 1.0)


def metrics(draws: dict) -> dict:
    """Per-draw metrics from the seven parameter draws (arrays of one shape),
    keyed by METRIC_NAMES: EVSI, EVPI, EVSI_ind (EVSI*), C = C_build + C_run,
    eta = EVSI/C, eta_ind = EVSI*/C, eta_run = EVSI/C_run and n_star =
    C_build / (EVSI - C_run) where EVSI > C_run else inf: the number of runs
    after which the evaluation has paid for its build (the break-even run
    count)."""
    p, s, t, B, K = (np.asarray(draws[k], dtype=float) for k in ("p", "s", "t", "B", "K"))
    C_build, C_run = (np.asarray(draws[k], dtype=float) for k in ("C_build", "C_run"))
    evsi, evpi = voi(p, s, t, B, K)
    evsi_ind = voi_indifference(p, s, t, B, K)
    C = C_build + C_run
    margin = evsi - C_run
    n_star = np.where(margin > 0.0, C_build / np.where(margin > 0.0, margin, 1.0), np.inf)
    return {
        "EVSI": evsi,
        "EVPI": evpi,
        "EVSI_ind": evsi_ind,
        "C": C,
        "eta": evsi / C,
        "eta_ind": evsi_ind / C,
        "eta_run": evsi / C_run,
        "n_star": n_star,
    }
