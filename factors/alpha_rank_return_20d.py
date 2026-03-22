FACTOR_NAME = "alpha_rank_return_20d"
FACTOR_DESC = "Percentile rank of 20-day return within own 120-day history"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 120

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    ret_20d = (closes[idx] - closes[idx - 20]) / closes[idx - 20] if closes[idx - 20] != 0 else 0.0
    count_below = 0
    total = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i - 20 >= 0 and closes[i - 20] != 0:
            r = (closes[i] - closes[i - 20]) / closes[i - 20]
            if r < ret_20d:
                count_below += 1
            total += 1
    if total == 0:
        return 0.5
    score = count_below / total
    return max(0.0, min(1.0, score))
