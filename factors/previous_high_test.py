"""
Factor: previous_high_test
Description: Price testing/approaching previous 20-day high
Category: support_resistance
"""

FACTOR_NAME = "previous_high_test"
FACTOR_DESC = "Price testing previous 20-day high — breakout potential"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """How close is price to the 20-day high (resistance test)."""
    lookback = 20
    if idx < lookback:
        return 0.5

    # Previous high (excluding today)
    prev_high = max(highs[idx - lookback + 1:idx])
    if prev_high <= 0:
        return 0.5

    price = closes[idx]
    distance_pct = (prev_high - price) / prev_high

    if price > prev_high:
        # Breakout above previous high!
        breakout_pct = (price - prev_high) / prev_high
        score = 0.8 + min(breakout_pct * 10, 0.15)
    elif distance_pct < 0.01:
        # Within 1% of previous high
        score = 0.75
    elif distance_pct < 0.03:
        score = 0.65
    elif distance_pct < 0.05:
        score = 0.6
    elif distance_pct < 0.10:
        score = 0.5
    else:
        score = 0.4

    return max(0.0, min(1.0, score))
