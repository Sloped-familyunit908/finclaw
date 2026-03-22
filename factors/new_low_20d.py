"""
Factor: new_low_20d
Description: Is price at or near 20-day low? (oversold)
Category: support_resistance
"""

FACTOR_NAME = "new_low_20d"
FACTOR_DESC = "Near 20-day low — potential oversold bounce"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """At 20-day low = oversold = potential bounce (bullish)."""
    lookback = 20
    if idx < lookback:
        return 0.5

    period_low = min(lows[idx - lookback + 1:idx + 1])
    period_high = max(highs[idx - lookback + 1:idx + 1])
    price_range = period_high - period_low

    if price_range <= 0:
        return 0.5

    price = closes[idx]

    # At the low = most oversold = highest bounce potential
    if lows[idx] <= period_low:
        # At new low — oversold bounce potential
        score = 0.7
    else:
        # Distance from low
        position = (price - period_low) / price_range

        if position < 0.1:
            score = 0.65  # Near low = oversold
        elif position < 0.2:
            score = 0.6
        elif position < 0.5:
            score = 0.5
        else:
            score = 0.45  # Far from low = less oversold

    return max(0.0, min(1.0, score))
