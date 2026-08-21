"""Sensitivity utilities (spec §4): Spearman correlations, rank stability
across scenarios, and cross-repeat elicitation noise."""

from __future__ import annotations

import numpy as np
from scipy import stats


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    """Spearman rank correlation; None when undefined (a constant vector)."""
    rho = stats.spearmanr(x, y).statistic
    if np.isnan(rho):
        return None
    return float(rho)


def rank_stability(eff: np.ndarray, top: int = 10) -> np.ndarray:
    """P(scenario in top-`top` by efficiency) across aligned MC draws.

    eff: (n_scenarios, n_draws). Ties (e.g. many zero-efficiency draws) are
    broken arbitrarily by argpartition; only relevant when fewer than `top`
    scenarios have positive efficiency in a draw.
    """
    n_scen, n_draws = eff.shape
    k = min(top, n_scen)
    top_idx = np.argpartition(-eff, k - 1, axis=0)[:k, :]
    counts = np.zeros(n_scen)
    np.add.at(counts, top_idx.ravel(), 1)
    return counts / n_draws


def repeat_spread(p50s) -> float | None:
    """Cross-repeat noise for one parameter of one scenario:
    (max - min) of p50 across repeats, relative to the pooled p50 (median of
    the repeat p50s). None when fewer than 2 repeats or pooled p50 == 0."""
    arr = np.asarray(list(p50s), dtype=float)
    if arr.size < 2:
        return None
    pooled = float(np.median(arr))
    if pooled == 0.0:
        return None
    return float((arr.max() - arr.min()) / abs(pooled))
