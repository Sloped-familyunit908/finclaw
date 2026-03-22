FACTOR_NAME = "drawdown_duration"
FACTOR_DESC = "Number of days since last all-time-high within 60-day window — shorter = bullish"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 60

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Find the most recent all-time high within the 60-day window
    max_close = closes[idx - LOOKBACK + 1]
    max_idx = idx - LOOKBACK + 1
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if closes[i] >= max_close:
            max_close = closes[i]
            max_idx = i
    days_since_high = idx - max_idx
    # 0 days = at high = very bullish; 60 days = extended drawdown
    score = 1.0 - days_since_high / LOOKBACK
    return max(0.0, min(1.0, score))
