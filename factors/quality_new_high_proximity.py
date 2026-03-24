"""
Quality Factor: New High Proximity
====================================
How close is current price to its 60-day high?
Near high = strong stock.  Far from high (>30% below) = weak/dying stock.

Category: quality_filter
"""

FACTOR_NAME = "quality_new_high_proximity"
FACTOR_DESC = "Proximity to 60-day high — far from high means weak/dying stock"
FACTOR_CATEGORY = "quality_filter"


def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0]."""
    lookback = min(60, idx + 1)
    if lookback < 5:
        return 0.5

    # Find 60-day high using highs array for accuracy
    peak = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] > peak:
            peak = highs[i]

    if peak <= 0:
        return 0.5

    # How close is current price to the peak?
    proximity = closes[idx] / peak  # 1.0 = at high, 0.7 = 30% below

    # Map: 0.70 -> 0.0, 0.85 -> 0.5, 1.0 -> 1.0
    score = (proximity - 0.70) / 0.30
    return max(0.0, min(1.0, score))
