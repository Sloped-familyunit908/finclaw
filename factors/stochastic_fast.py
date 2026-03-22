FACTOR_NAME = "stochastic_fast"
FACTOR_DESC = "Fast stochastic %K (14-day)"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 14

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
    denom = highest - lowest
    if denom == 0:
        return 0.5
    pct_k = (closes[idx] - lowest) / denom
    return max(0.0, min(1.0, pct_k))
