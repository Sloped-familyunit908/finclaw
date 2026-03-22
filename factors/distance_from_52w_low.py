"""
Auto-generated factor: distance_from_52w_low
Description: Distance from 252-day (1-year) low
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "distance_from_52w_low"
FACTOR_DESC = "Distance from 252-day (1-year) low"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Percentage distance from 252-day low."""

    lookback = 252
    if idx < lookback:
        return 0.5

    # Find 252-day low
    min_low = lows[idx - lookback]
    for i in range(idx - lookback, idx + 1):
        if lows[i] < min_low:
            min_low = lows[i]

    if min_low < 1e-10:
        return 0.5

    # Distance from low as percentage
    dist_pct = (closes[idx] - min_low) / min_low

    # Far above 52w low = strong = bullish
    # Near 52w low = weak = bearish
    # Map: 0% above = 0.1, 100% above = 0.9
    score = 0.1 + dist_pct * 0.8
    return max(0.0, min(1.0, score))
