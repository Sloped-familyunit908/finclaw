"""
Factor: volume_trend
Description: Is volume trending up or down over last 20 days (linear regression)
Category: volume
"""

FACTOR_NAME = "volume_trend"
FACTOR_DESC = "Volume trending up or down over last 20 days via linear regression"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Linear regression slope of volume over 20 days."""
    period = 20
    if idx < period:
        return 0.5

    # Simple linear regression of volume
    n = period
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0

    for i in range(n):
        x = float(i)
        y = float(volumes[idx - period + 1 + i])
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_x2 += x * x

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.5

    slope = (n * sum_xy - sum_x * sum_y) / denom
    avg_vol = sum_y / n if n > 0 else 1.0
    if avg_vol <= 0:
        return 0.5

    # Normalize slope relative to average volume
    normalized_slope = slope / avg_vol

    # Map: -0.05 → 0.0, 0 → 0.5, +0.05 → 1.0
    score = 0.5 + normalized_slope * 10.0

    return max(0.0, min(1.0, score))
