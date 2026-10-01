"""Sensitivity utilities the Monte Carlo run stores: Spearman correlations of
parameter draws against efficiency and the rank stability across scenarios."""

from __future__ import annotations

import numpy as np
from scipy import stats


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    """Spearman rank correlation; None when undefined (a constant vector)."""
    rho = stats.spearmanr(x, y).statistic
    if np.isnan(rho):
        return None
    return float(rho)


def rank_stability(eff: np.ndarray, top: int = 5) -> np.ndarray:
    """P(scenario in top-`top` by efficiency AND efficiency > 0) across aligned
    MC draws.

    eff: (n_scenarios, n_draws). Zero-efficiency scenarios never count as top
    members: when fewer than `top` scenarios are positive in a draw,
    argpartition would otherwise fill the remaining slots arbitrarily (by
    index) among the tied zeros, biasing the probability toward low scenario
    ids.
    """
    n_scen, n_draws = eff.shape
    k = min(top, n_scen)
    top_idx = np.argpartition(-eff, k - 1, axis=0)[:k, :]
    top_val = np.take_along_axis(eff, top_idx, axis=0)
    counts = np.zeros(n_scen)
    np.add.at(counts, top_idx[top_val > 0.0], 1)
    return counts / n_draws
