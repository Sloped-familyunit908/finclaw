FACTOR_NAME = "worst_day_recency"
FACTOR_DESC = "How many days ago was the worst day in last 20 days — recent worst is bearish"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    worst_ret = 999.0
    worst_ago = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        if ret < worst_ret:
            worst_ret = ret
            worst_ago = idx - i
    # worst_ago: 0 = today (worst is recent = bearish), LOOKBACK-1 = far ago (bullish)
    score = worst_ago / LOOKBACK
    return max(0.0, min(1.0, score))
