"""
Auto-generated factor: distance_from_52w_high
Description: Distance from 252-day (1-year) high
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "distance_from_52w_high"
FACTOR_DESC = "Distance from 252-day (1-year) high"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Percentage distance from 252-day high."""

    lookback = 252
    if idx < lookback:
        return 0.5

    # Find 252-day high
    max_high = highs[idx - lookback]
    for i in range(idx - lookback, idx + 1):
        if highs[i] > max_high:
            max_high = highs[i]

    if max_high < 1e-10:
        return 0.5

    # Distance as percentage
    dist_pct = (max_high - closes[idx]) / max_high

    # Near 52w high = strong momentum = bullish
    # Far from 52w high = weak = bearish
    # Map: 0% away = 0.9, 50% away = 0.1
    score = 0.9 - dist_pct * 1.6
    return max(0.0, min(1.0, score))
