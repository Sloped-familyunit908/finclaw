"""
Factor: crypto_mean_reversion_speed
Description: How fast price reverts to 48h mean after deviation
Category: crypto
"""

FACTOR_NAME = "crypto_mean_reversion_speed"
FACTOR_DESC = "Speed of price reversion to 48h mean after deviation"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = fast mean reversion (mean-reverting regime)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    mean_price = sum(closes[idx - lookback:idx]) / lookback
    if mean_price <= 0:
        return 0.5

    # Measure deviations and how quickly they shrink
    deviations = []
    for i in range(idx - lookback, idx):
        dev = abs(closes[i] - mean_price) / mean_price
        deviations.append(dev)

    if len(deviations) < 4:
        return 0.5

    # Compare recent deviations vs earlier ones
    half = len(deviations) // 2
    early_avg = sum(deviations[:half]) / half
    late_avg = sum(deviations[half:]) / (len(deviations) - half)

    if early_avg <= 0:
        return 0.5

    # If deviations are shrinking, mean reversion is occurring
    reversion_ratio = 1.0 - (late_avg / early_avg)
    # Positive = converging, negative = diverging
    score = 0.5 + reversion_ratio * 0.5
    return max(0.0, min(1.0, score))
