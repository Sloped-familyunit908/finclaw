"""
Factor: crypto_market_depth
Description: Rolling std of (high-low)/close — market depth proxy
Category: crypto
"""

FACTOR_NAME = "crypto_market_depth"
FACTOR_DESC = "Rolling std of range/close ratio — stable depth = healthy market"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = stable market depth, Low = unstable."""
    import math

    lookback = 24
    if idx < lookback:
        return 0.5

    ratios = []
    for i in range(idx - lookback, idx + 1):
        if closes[i] > 0:
            ratios.append((highs[i] - lows[i]) / closes[i])

    if len(ratios) < 5:
        return 0.5

    mean_r = sum(ratios) / len(ratios)
    if mean_r <= 0:
        return 0.5

    variance = sum((r - mean_r) ** 2 for r in ratios) / len(ratios)
    std = math.sqrt(variance) if variance > 0 else 0

    # Coefficient of variation: std/mean
    cv = std / mean_r

    # Low CV = stable depth = good → high score
    # High CV = unstable depth = risky → low score
    # CV typically ranges from 0.1 to 2.0 in crypto
    score = 1.0 - min(cv / 2.0, 1.0)

    return max(0.0, min(1.0, score))
