"""
Factor: momentum_10d
Description: 10-day price momentum
Category: momentum
"""

FACTOR_NAME = "momentum_10d"
FACTOR_DESC = "10-day price momentum — medium-term rate of change"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """10-day price change as momentum signal."""
    period = 10
    if idx < period:
        return 0.5

    prev = closes[idx - period]
    if prev <= 0:
        return 0.5

    roc = (closes[idx] - prev) / prev

    # Normalize: -10% → 0.0, 0% → 0.5, +10% → 1.0
    score = 0.5 + roc * 5.0

    return max(0.0, min(1.0, score))
