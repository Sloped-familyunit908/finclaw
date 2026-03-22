"""
Auto-generated factor: return_consistency
Description: Standard deviation of daily returns over 20 days (lower = more consistent)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "return_consistency"
FACTOR_DESC = "Standard deviation of daily returns over 20 days (lower = more consistent)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Return consistency: lower volatility = higher score."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Collect returns
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

    if len(returns) < 5:
        return 0.5

    mean_ret = sum(returns) / len(returns)
    var_sum = 0.0
    for r in returns:
        var_sum += (r - mean_ret) ** 2
    std = (var_sum / len(returns)) ** 0.5

    # Lower std = more consistent = higher score
    # Typical daily std: 0.01 to 0.05
    # Map: 0% std = 1.0, 5% std = 0.0
    score = 1.0 - std * 20.0
    return max(0.0, min(1.0, score))
