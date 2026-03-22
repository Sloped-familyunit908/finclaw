FACTOR_NAME = "midpoint_reversion"
FACTOR_DESC = "Distance from midpoint of 20-day range — extreme = reversion expected"
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
    mid = (highest + lowest) / 2.0
    channel_range = highest - lowest
    if channel_range == 0:
        return 0.5
    # Below midpoint = oversold = bullish reversion; above = overbought = bearish
    deviation = (mid - closes[idx]) / channel_range  # positive when below mid
    score = 0.5 + deviation
    return max(0.0, min(1.0, score))
