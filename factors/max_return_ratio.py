FACTOR_NAME = "max_return_ratio"
FACTOR_DESC = "Today's return / max(abs(returns)) last 60 days — normalized move size"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 60

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if closes[idx - 1] == 0:
        return 0.5
    today_ret = (closes[idx] - closes[idx - 1]) / closes[idx - 1]
    max_abs = 0.0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        r = abs((closes[i] - closes[i - 1]) / closes[i - 1])
        if r > max_abs:
            max_abs = r
    if max_abs == 0:
        return 0.5
    ratio = today_ret / max_abs  # [-1, 1]
    score = 0.5 + ratio * 0.5
    return max(0.0, min(1.0, score))
