"""
Factor: new_high_20d
Description: Is price at or near 20-day high? (momentum)
Category: support_resistance
"""

FACTOR_NAME = "new_high_20d"
FACTOR_DESC = "New 20-day high — strong momentum signal"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Score based on proximity to 20-day high."""
    lookback = 20
    if idx < lookback:
        return 0.5

    period_high = max(highs[idx - lookback + 1:idx + 1])
    period_low = min(lows[idx - lookback + 1:idx + 1])
    price_range = period_high - period_low

    if price_range <= 0:
        return 0.5

    price = closes[idx]

    # At the 20-day high
    if highs[idx] >= period_high:
        score = 0.9
    else:
        # How close to the high
        position = (price - period_low) / price_range
        # Scale from 0.2 to 0.85
        score = 0.2 + position * 0.65

    return max(0.0, min(1.0, score))
