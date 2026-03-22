FACTOR_NAME = "stochastic_slow"
FACTOR_DESC = "Slow stochastic %D — 3-day SMA of %K (14-day)"
FACTOR_CATEGORY = "price_structure"
LOOKBACK = 16

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Compute %K for last 3 days, then average
    pct_k_sum = 0.0
    for d in range(3):
        day = idx - 2 + d
        highest = highs[day - 13]
        lowest = lows[day - 13]
        for i in range(day - 13, day + 1):
            if highs[i] > highest:
                highest = highs[i]
            if lows[i] < lowest:
                lowest = lows[i]
        denom = highest - lowest
        if denom == 0:
            pct_k_sum += 0.5
        else:
            pct_k_sum += (closes[day] - lowest) / denom
    pct_d = pct_k_sum / 3.0
    return max(0.0, min(1.0, pct_d))
