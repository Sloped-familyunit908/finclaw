FACTOR_NAME = "outperformance_20d"
FACTOR_DESC = "20-day return vs 120-day average return"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 120

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if closes[idx - 20] == 0:
        return 0.5
    ret_20d = (closes[idx] - closes[idx - 20]) / closes[idx - 20]
    total = 0.0
    count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i - 20 >= 0 and closes[i - 20] != 0:
            r = (closes[i] - closes[i - 20]) / closes[i - 20]
            total += r
            count += 1
    if count == 0:
        return 0.5
    avg_ret = total / count
    diff = ret_20d - avg_ret
    score = 0.5 + diff * 10.0
    return max(0.0, min(1.0, score))
