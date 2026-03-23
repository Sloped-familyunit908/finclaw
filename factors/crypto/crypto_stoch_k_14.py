"""
Factor: crypto_stoch_k_14
Description: %K stochastic 14 bars
Category: crypto
"""

FACTOR_NAME = "crypto_stoch_k_14"
FACTOR_DESC = "%K stochastic 14 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Raw %K stochastic value."""
    lookback = 14
    if idx < lookback:
        return 0.5

    highest = max(highs[idx - lookback:idx])
    lowest = min(lows[idx - lookback:idx])
    r = highest - lowest
    if r <= 0:
        return 0.5

    k = (closes[idx - 1] - lowest) / r
    return max(0.0, min(1.0, k))
