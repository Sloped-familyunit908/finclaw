"""
Auto-generated factor: momentum_quality
Description: Return / volatility over last 20 days (risk-adjusted momentum)
Category: composite
Generated: seed
"""

FACTOR_NAME = "momentum_quality"
FACTOR_DESC = "Return / volatility over last 20 days (risk-adjusted momentum)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Risk-adjusted momentum: return / volatility."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Total return
    total_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0.0

    # Volatility (std of daily returns)
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
    vol = (var_sum / len(returns)) ** 0.5

    if vol < 1e-10:
        return 0.5 if abs(total_return) < 1e-10 else (0.8 if total_return > 0 else 0.2)

    # Risk-adjusted momentum
    ram = total_return / vol

    # Map from [-3, 3] to [0, 1]
    score = 0.5 + ram / 6.0
    return max(0.0, min(1.0, score))
