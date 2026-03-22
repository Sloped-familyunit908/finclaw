FACTOR_NAME = "outperformance_5d"
FACTOR_DESC = "5-day return compared to stock's own 60-day average return"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 60

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if closes[idx - 5] == 0:
        return 0.5
    ret_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5]
    # Average 5-day return over last 60 days
    total = 0.0
    count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i - 5 >= 0 and closes[i - 5] != 0:
            r = (closes[i] - closes[i - 5]) / closes[i - 5]
            total += r
            count += 1
    if count == 0:
        return 0.5
    avg_ret = total / count
    diff = ret_5d - avg_ret
    score = 0.5 + diff * 20.0
    return max(0.0, min(1.0, score))
