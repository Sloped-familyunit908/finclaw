"""
Auto-generated factor: quality_momentum
Description: Stocks with low volatility but positive returns (quality factor proxy)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "quality_momentum"
FACTOR_DESC = "Stocks with low volatility but positive returns (quality factor proxy)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Quality momentum: positive returns with low volatility."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Calculate returns
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)

    # Mean return
    mean_ret = sum(returns) / len(returns)

    # Std of returns
    var_sum = 0.0
    for r in returns:
        var_sum += (r - mean_ret) ** 2
    std_ret = (var_sum / len(returns)) ** 0.5

    if std_ret < 1e-10:
        return 0.5 if mean_ret == 0 else (0.7 if mean_ret > 0 else 0.3)

    # Quality = positive return / low volatility
    # Higher return and lower vol = better quality
    quality = mean_ret / std_ret  # This is like a Sharpe ratio

    # Map from [-2, 2] to [0, 1]
    score = 0.5 + quality * 0.25
    return max(0.0, min(1.0, score))
