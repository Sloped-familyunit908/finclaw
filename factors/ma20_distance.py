"""
Factor: ma20_distance
Description: Distance from 20-day MA as percentage, normalized
Category: moving_average
"""

FACTOR_NAME = "ma20_distance"
FACTOR_DESC = "Distance from 20-day MA as percentage, normalized"
FACTOR_CATEGORY = "moving_average"


def compute(closes, highs, lows, volumes, idx):
    """Percentage distance from MA20. Positive = above MA (bullish)."""
    period = 20
    if idx < period:
        return 0.5

    ma = sum(closes[idx - period + 1:idx + 1]) / period
    if ma <= 0:
        return 0.5

    pct_distance = (closes[idx] - ma) / ma

    # Normalize: -15% maps to 0.0, 0% maps to 0.5, +15% maps to 1.0
    score = 0.5 + pct_distance * (0.5 / 0.15)

    return max(0.0, min(1.0, score))
