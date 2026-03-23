"""
Factor: crypto_buying_pressure
Description: (close-low)/(high-low) averaged over 12 bars — measures buying pressure
Category: crypto
"""

FACTOR_NAME = "crypto_buying_pressure"
FACTOR_DESC = "(close-low)/(high-low) averaged over 12 bars — buying pressure indicator"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong buying pressure."""
    lookback = 12
    if idx < lookback:
        return 0.5

    total = 0.0
    count = 0
    for i in range(idx - lookback, idx):
        rng = highs[i] - lows[i]
        if rng > 0:
            total += (closes[i] - lows[i]) / rng
            count += 1

    if count == 0:
        return 0.5

    avg_pressure = total / count
    return max(0.0, min(1.0, avg_pressure))
