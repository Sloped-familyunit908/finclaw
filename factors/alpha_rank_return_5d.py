FACTOR_NAME = "alpha_rank_return_5d"
FACTOR_DESC = "Percentile rank of 5-day return within own 60-day history"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 60

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    ret_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5] if closes[idx - 5] != 0 else 0.0
    count_below = 0
    total = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i - 5 >= 0 and closes[i - 5] != 0:
            r = (closes[i] - closes[i - 5]) / closes[i - 5]
            if r < ret_5d:
                count_below += 1
            total += 1
    if total == 0:
        return 0.5
    score = count_below / total
    return max(0.0, min(1.0, score))
