"""
Auto-generated factor: sharpe_20d
Description: 20-day rolling Sharpe ratio (mean return / std return)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "sharpe_20d"
FACTOR_DESC = "20-day rolling Sharpe ratio (mean return / std return)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """20-day rolling Sharpe ratio."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Collect daily returns
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

    if std < 1e-10:
        return 0.5 if abs(mean_ret) < 1e-10 else (0.8 if mean_ret > 0 else 0.2)

    sharpe = mean_ret / std

    # Map Sharpe from [-2, 2] to [0, 1]
    score = 0.5 + sharpe * 0.25
    return max(0.0, min(1.0, score))
