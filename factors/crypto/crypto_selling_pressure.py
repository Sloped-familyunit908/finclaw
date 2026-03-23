"""
Factor: crypto_selling_pressure
Description: (high-close)/(high-low) averaged over 12 bars — measures selling pressure
Category: crypto
"""

FACTOR_NAME = "crypto_selling_pressure"
FACTOR_DESC = "(high-close)/(high-low) averaged over 12 bars — selling pressure indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong selling pressure (bearish)."""
    lookback = 12
    if idx < lookback:
        return 0.5

    total = 0.0
    count = 0
    for i in range(idx - lookback, idx):
        rng = highs[i] - lows[i]
        if rng > 0:
            total += (highs[i] - closes[i]) / rng
            count += 1

    if count == 0:
        return 0.5

    avg_pressure = total / count
    # High selling pressure → low score (bearish), low selling pressure → high score
    return max(0.0, min(1.0, 1.0 - avg_pressure))
