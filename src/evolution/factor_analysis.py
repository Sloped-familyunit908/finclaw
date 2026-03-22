"""
Factor Analysis Tools for FinClaw
Provides IC (Information Coefficient) and IR (Information Ratio) analysis.
"""
import numpy as np
from typing import Dict, List, Tuple


def compute_ic(factor_scores: List[float], forward_returns: List[float]) -> float:
    """Compute Information Coefficient (rank correlation between factor and returns).

    IC measures how well a factor predicts future returns.
    IC > 0.05 is generally considered useful.
    IC > 0.1 is very strong.
    """
    if len(factor_scores) < 10:
        return 0.0
    # Spearman rank correlation
    n = len(factor_scores)
    rank_factor = _rank(factor_scores)
    rank_returns = _rank(forward_returns)
    d_squared = sum((rf - rr) ** 2 for rf, rr in zip(rank_factor, rank_returns))
    ic = 1 - (6 * d_squared) / (n * (n * n - 1))
    return round(ic, 4)


def compute_ir(ic_series: List[float]) -> float:
    """Compute Information Ratio (mean IC / std IC).

    IR measures consistency of a factor's predictive power.
    IR > 0.5 is good. IR > 1.0 is excellent.
    """
    if len(ic_series) < 5:
        return 0.0
    mean_ic = np.mean(ic_series)
    std_ic = np.std(ic_series)
    if std_ic < 0.0001:
        return 0.0
    return round(float(mean_ic / std_ic), 4)


def compute_factor_returns(
    factor_scores: Dict[str, float],
    forward_returns: Dict[str, float],
    n_groups: int = 5,
) -> Dict[str, float]:
    """Compute long-short factor returns by quintile.

    Sorts stocks by factor score, computes returns for each quintile.
    Returns dict with 'long_short', 'top_quintile', 'bottom_quintile'.
    """
    if len(factor_scores) < n_groups * 2:
        return {"long_short": 0.0, "top_quintile": 0.0, "bottom_quintile": 0.0}

    # Sort stocks by factor score
    sorted_stocks = sorted(factor_scores.keys(), key=lambda s: factor_scores[s])
    group_size = len(sorted_stocks) // n_groups

    # Bottom quintile (lowest factor scores)
    bottom = sorted_stocks[:group_size]
    bottom_ret = float(np.mean([forward_returns.get(s, 0) for s in bottom]))

    # Top quintile (highest factor scores)
    top = sorted_stocks[-group_size:]
    top_ret = float(np.mean([forward_returns.get(s, 0) for s in top]))

    return {
        "long_short": round(top_ret - bottom_ret, 4),
        "top_quintile": round(top_ret, 4),
        "bottom_quintile": round(bottom_ret, 4),
    }


def analyze_factor_decay(
    factor_scores: Dict[str, float],
    multi_period_returns: Dict[str, List[float]],  # code -> [1d, 2d, 5d, 10d, 20d returns]
    periods: List[int] = [1, 2, 5, 10, 20],
) -> Dict[int, float]:
    """Analyze how factor predictive power decays over time.

    Returns IC for each forward period.
    """
    decay = {}
    scores_list = [factor_scores[c] for c in factor_scores]

    for i, period in enumerate(periods):
        returns_list = [multi_period_returns[c][i] for c in factor_scores if c in multi_period_returns]
        if len(returns_list) == len(scores_list):
            decay[period] = compute_ic(scores_list, returns_list)
        else:
            decay[period] = 0.0

    return decay


def _rank(values: List[float]) -> List[float]:
    """Compute ranks (1-based, average for ties)."""
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks
