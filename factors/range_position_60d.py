"""
Factor: range_position_60d
Description: Position within 60-day range (0=at low, 1=at high)
Category: support_resistance
"""

FACTOR_NAME = "range_position_60d"
FACTOR_DESC = "Position within 60-day price range — 0=at low, 1=at high"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Where is current price within its 60-day range."""
    lookback = 60
    if idx < lookback:
        return 0.5

    period_high = highs[idx - lookback + 1]
    period_low = lows[idx - lookback + 1]

    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] > period_high:
            period_high = highs[i]
        if lows[i] < period_low:
            period_low = lows[i]

    price_range = period_high - period_low
    if price_range <= 0:
        return 0.5

    position = (closes[idx] - period_low) / price_range

    return max(0.0, min(1.0, position))
