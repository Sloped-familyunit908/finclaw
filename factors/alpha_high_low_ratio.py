FACTOR_NAME = "alpha_high_low_ratio"
FACTOR_DESC = "Average (close - low) / (high - low) over 10 days — where close sits in daily range"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 10

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    total = 0.0
    count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        spread = highs[i] - lows[i]
        if spread > 0:
            ratio = (closes[i] - lows[i]) / spread
            total += ratio
            count += 1
    if count == 0:
        return 0.5
    score = total / count
    return max(0.0, min(1.0, score))
