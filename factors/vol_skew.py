"""
Factor: vol_skew
Description: Asymmetry of returns (more big down moves vs big up moves)
Category: volatility
"""

FACTOR_NAME = "vol_skew"
FACTOR_DESC = "Return skewness — negative skew means more crashes, positive = more rallies"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Skewness of returns over 20 days. Positive skew = bullish asymmetry."""
    period = 20
    if idx < period + 1:
        return 0.5

    returns = []
    for i in range(idx - period + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    n = len(returns)
    if n < 3:
        return 0.5

    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    std = variance ** 0.5

    if std <= 0:
        return 0.5

    # Skewness = E[(x - mean)^3] / std^3
    skew = sum((r - mean_r) ** 3 for r in returns) / (n * std ** 3)

    # Map: skew -2 → 0.1, 0 → 0.5, +2 → 0.9
    score = 0.5 + skew * 0.2

    return max(0.0, min(1.0, score))
