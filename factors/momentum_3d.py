"""
Factor: momentum_3d
Description: 3-day price momentum (short-term)
Category: momentum
"""

FACTOR_NAME = "momentum_3d"
FACTOR_DESC = "3-day price momentum — short-term rate of change"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """3-day price change as momentum signal."""
    period = 3
    if idx < period:
        return 0.5

    prev = closes[idx - period]
    if prev <= 0:
        return 0.5

    roc = (closes[idx] - prev) / prev

    # Normalize: -5% → 0.0, 0% → 0.5, +5% → 1.0
    score = 0.5 + roc * 10.0

    return max(0.0, min(1.0, score))
