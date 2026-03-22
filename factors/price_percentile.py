"""
Auto-generated factor: price_percentile
Description: Where is current price relative to its 120-day range — 0=at low, 1=at high
Category: momentum
Generated: seed
"""

FACTOR_NAME = "price_percentile"
FACTOR_DESC = "Where is current price relative to its 120-day range — 0=at low, 1=at high"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """(close - 120d_low) / (120d_high - 120d_low)"""

    lookback = 120
    if idx < lookback:
        return 0.5

    current_close = closes[idx]

    # Find 120-day high and low using highs/lows arrays
    period_high = highs[idx - lookback + 1]
    period_low = lows[idx - lookback + 1]
    for i in range(idx - lookback + 1, idx + 1):
        if highs[i] > period_high:
            period_high = highs[i]
        if lows[i] < period_low:
            period_low = lows[i]

    range_size = period_high - period_low
    if range_size <= 0:
        return 0.5

    score = (current_close - period_low) / range_size
    return max(0.0, min(1.0, score))
