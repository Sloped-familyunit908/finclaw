"""
Factor: crypto_kurtosis_24h
Description: Kurtosis of 24h returns (tail fatness)
Category: crypto
"""

FACTOR_NAME = "crypto_kurtosis_24h"
FACTOR_DESC = "Kurtosis of 24-hour return distribution"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = fatter tails (more extreme moves)."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 4:
        return 0.5

    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    std = variance ** 0.5

    if std <= 0:
        return 0.5

    kurtosis = sum((r - mean_r) ** 4 for r in returns) / (n * std ** 4)

    # Excess kurtosis (normal = 3, so excess = kurtosis - 3)
    excess_k = kurtosis - 3.0

    # Typical range: -2 to 10
    score = (excess_k + 2) / 12.0
    return max(0.0, min(1.0, score))
