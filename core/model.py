"""Closed-form EVSI / EVPI for the binary-state, binary-signal, binary-action
decision problem (spec §2.3). Vectorized over NumPy arrays.

Convention: theta=1 is the state in which responding (a=1) is the correct
action. Utilities are in the regret parameterization with u(theta, a=0) = 0.
"""

import numpy as np


def value_of_acting(pi, e, B, K):
    """V(pi) = max(0, pi*e*B - (1-pi)*K): value of acting optimally at belief pi."""
    return np.maximum(0.0, pi * e * B - (1.0 - pi) * K)


def voi(p, s, t, e, B, K):
    """Return (EVSI, EVPI), broadcasting over array inputs.

    Guards: if P(x=1) or P(x=0) is zero, that branch contributes 0.
    EVSI is clipped into [0, EVPI], which holds mathematically; the clip only
    removes last-ulp floating-point noise.
    """
    p, s, t, e, B, K = (np.asarray(v, dtype=float) for v in (p, s, t, e, B, K))
    P1 = p * s + (1.0 - p) * (1.0 - t)
    P0 = 1.0 - P1
    pi1 = np.where(P1 > 0.0, p * s / np.where(P1 > 0.0, P1, 1.0), 0.0)
    pi0 = np.where(P0 > 0.0, p * (1.0 - s) / np.where(P0 > 0.0, P0, 1.0), 0.0)
    evsi = (
        P1 * value_of_acting(pi1, e, B, K)
        + P0 * value_of_acting(pi0, e, B, K)
        - value_of_acting(p, e, B, K)
    )
    evpi = np.minimum(p * e * B, (1.0 - p) * K)
    evsi = np.minimum(np.maximum(evsi, 0.0), evpi)
    return evsi, evpi
