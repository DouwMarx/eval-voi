"""Closed-form EVSI / EVPI for the binary-state, binary-signal, binary-action
decision problem (spec §2.3). Vectorized over NumPy arrays.

Convention: theta=1 is the state in which responding (a=1) is the correct
action. Utilities are in the regret parameterization with u(theta, a=0) = 0,
u(1,1) = B, u(0,1) = -K. v2 dropped the v1 efficacy multiplier e (see spec,
"v2 changes").
"""

import numpy as np


def value_of_acting(pi, B, K):
    """V(pi) = max(0, pi*B - (1-pi)*K): value of acting optimally at belief pi."""
    return np.maximum(0.0, pi * B - (1.0 - pi) * K)


def voi(p, s, t, B, K):
    """Return (EVSI, EVPI), broadcasting over array inputs.

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


def voi_fence(p, s, t, B, K):
    """EVSI* = Lambda p (1 - p) (s + t - 1), Lambda = B + K: the maximum of
    EVSI over the threshold pi* = K / (B + K) at fixed stakes Lambda, reached
    by the buyer on the fence, pi* = p (chapter, "The buyer on the fence, and
    bounds", eq. fence). Stakes times the Bernoulli variance of the state
    times Youden's index: smooth in every input and positive whenever the
    sensor is informative, so it ranks scenarios without the gate. An
    inverted sensor (s + t < 1, which the elicitation rejects but a mixture
    draw can produce) is read the other way round, |s + t - 1|, as voi does."""
    p, s, t, B, K = (np.asarray(v, dtype=float) for v in (p, s, t, B, K))
    return (B + K) * p * (1.0 - p) * np.abs(s + t - 1.0)
