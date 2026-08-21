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
    """P(scenario in top-`top` by efficiency AND efficiency > 0) across aligned
    MC draws.

    eff: (n_scenarios, n_draws). Zero-efficiency scenarios never count as top
    members: when fewer than `top` scenarios are positive in a draw,
    argpartition would otherwise fill the remaining slots arbitrarily (by
    index) among the tied zeros, biasing p_top10 toward low scenario ids.
    """
    n_scen, n_draws = eff.shape
    k = min(top, n_scen)
    top_idx = np.argpartition(-eff, k - 1, axis=0)[:k, :]
    top_val = np.take_along_axis(eff, top_idx, axis=0)
    counts = np.zeros(n_scen)
    np.add.at(counts, top_idx[top_val > 0.0], 1)
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
