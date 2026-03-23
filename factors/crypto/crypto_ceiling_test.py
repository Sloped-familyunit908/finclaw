"""
Factor: crypto_ceiling_test
Description: Price testing recent resistance (within 0.5% of 48h high)
Category: crypto
"""

FACTOR_NAME = "crypto_ceiling_test"
FACTOR_DESC = "Price near 48h high — testing resistance/ceiling"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price at resistance (could break or reject)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    high_48h = max(highs[idx - lookback:idx])
    if high_48h <= 0:
        return 0.5

    distance = (high_48h - closes[idx]) / high_48h

    # Within 0.5% of high = testing resistance
    if distance < 0.005:
        # Count how many times this level has been tested
        tests = 0
        for i in range(idx - lookback, idx):
            if (high_48h - highs[i]) / high_48h < 0.005:
                tests += 1
        # More tests = stronger resistance = more significant
        strength = min(tests / 5.0, 1.0)
        score = 0.5 + strength * 0.4
        return max(0.0, min(1.0, score))

    # Not near resistance
    return 0.5
