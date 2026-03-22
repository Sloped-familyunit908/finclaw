FACTOR_NAME = "price_channel_upper"
FACTOR_DESC = "Distance from 20-day highest high, normalized"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    highest = highs[idx - LOOKBACK + 1]
    lowest = lows[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if highs[i] > highest:
            highest = highs[i]
        if lows[i] < lowest:
            lowest = lows[i]
    channel_range = highest - lowest
    if channel_range == 0:
        return 0.5
    # How close is current close to the upper channel
    score = (closes[idx] - lowest) / channel_range
    return max(0.0, min(1.0, score))
