"""
Factor: trend_strength_slope
Description: Slope of linear regression over last 30 days, normalized
Category: momentum
"""

FACTOR_NAME = "trend_strength_slope"
FACTOR_DESC = "Trend strength via linear regression slope over 30 days"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Linear regression slope of closes over 30 days, normalized by price."""
    period = 30
    if idx < period:
        return 0.5

    n = period
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_x2 = 0.0

    for i in range(n):
        x = float(i)
        y = float(closes[idx - period + 1 + i])
        sum_x += x
        sum_y += y
        sum_xy += x * y
        sum_x2 += x * x

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.5

    slope = (n * sum_xy - sum_x * sum_y) / denom
    avg_price = sum_y / n
    if avg_price <= 0:
        return 0.5

    # Normalize slope as daily % change
    normalized = slope / avg_price

    # Map: -0.5% per day → 0.0, 0 → 0.5, +0.5% per day → 1.0
    score = 0.5 + normalized * 100.0

    return max(0.0, min(1.0, score))
