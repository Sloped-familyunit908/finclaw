FACTOR_NAME = "price_channel_lower"
FACTOR_DESC = "Distance from 20-day lowest low, normalized — close to low is bullish (bounce potential)"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    lowest = lows[idx - LOOKBACK + 1]
    highest = highs[idx - LOOKBACK + 1]
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if lows[i] < lowest:
            lowest = lows[i]
        if highs[i] > highest:
            highest = highs[i]
    channel_range = highest - lowest
    if channel_range == 0:
        return 0.5
    # Distance from lower band — close to lower = oversold = bullish reversal potential
    dist_from_low = (closes[idx] - lowest) / channel_range
    # Invert: close to low = high score (contrarian)
    score = 1.0 - dist_from_low
    return max(0.0, min(1.0, score))
