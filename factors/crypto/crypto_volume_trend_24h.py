"""
Factor: crypto_volume_trend_24h
Description: Linear regression slope of volume over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_volume_trend_24h"
FACTOR_DESC = "Volume trend direction via linear regression slope over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = volume trending up, Low = trending down."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Simple linear regression slope: sum((x-xmean)(y-ymean)) / sum((x-xmean)^2)
    vols = volumes[idx - lookback:idx]
    n = lookback
    x_mean = (n - 1) / 2.0
    y_mean = sum(vols) / n

    if y_mean <= 0:
        return 0.5

    numerator = 0.0
    denominator = 0.0
    for i in range(n):
        x_diff = i - x_mean
        y_diff = vols[i] - y_mean
        numerator += x_diff * y_diff
        denominator += x_diff * x_diff

    if denominator <= 0:
        return 0.5

    slope = numerator / denominator
    # Normalize slope relative to mean volume
    norm_slope = slope / y_mean  # slope per bar as fraction of mean
    score = 0.5 + norm_slope * 50.0  # Scale for visibility
    return max(0.0, min(1.0, score))
