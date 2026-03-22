"""
Factor: volume_at_high
Description: Volume when price is near 20-day high vs near 20-day low
Category: volume
"""

FACTOR_NAME = "volume_at_high"
FACTOR_DESC = "Volume when price is near 20-day high vs near 20-day low"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """More volume at highs = distribution (bearish), more at lows = accumulation (bullish)."""
    lookback = 20
    if idx < lookback:
        return 0.5

    period_high = max(highs[idx - lookback + 1:idx + 1])
    period_low = min(lows[idx - lookback + 1:idx + 1])
    price_range = period_high - period_low

    if price_range <= 0:
        return 0.5

    vol_near_high = 0.0
    vol_near_low = 0.0
    threshold = 0.25  # top/bottom 25% of range

    high_level = period_high - price_range * threshold
    low_level = period_low + price_range * threshold

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] >= high_level:
            vol_near_high += volumes[i]
        elif closes[i] <= low_level:
            vol_near_low += volumes[i]

    total = vol_near_high + vol_near_low
    if total <= 0:
        return 0.5

    # More volume at lows = accumulation = bullish
    low_ratio = vol_near_low / total

    # Map: all volume at lows = 0.85 (bullish accumulation)
    # all volume at highs = 0.15 (bearish distribution)
    score = 0.15 + low_ratio * 0.7

    return max(0.0, min(1.0, score))
