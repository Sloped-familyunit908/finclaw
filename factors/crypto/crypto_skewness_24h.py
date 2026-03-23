"""
Factor: crypto_skewness_24h
Description: Skewness of 24h returns (direction of fat tails)
Category: crypto
"""

FACTOR_NAME = "crypto_skewness_24h"
FACTOR_DESC = "Skewness of 24-hour return distribution"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = positive skew (right tail), below = negative skew."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 3:
        return 0.5

    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    std = variance ** 0.5

    if std <= 0:
        return 0.5

    skewness = sum((r - mean_r) ** 3 for r in returns) / (n * std ** 3)

    # Typical range: -2 to +2
    score = 0.5 + (skewness / 4.0)
    return max(0.0, min(1.0, score))
