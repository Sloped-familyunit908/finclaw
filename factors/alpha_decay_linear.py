FACTOR_NAME = "alpha_decay_linear"
FACTOR_DESC = "Linear-weighted return: recent days weighted more (decay factor)"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 10

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    weighted_sum = 0.0
    weight_total = 0.0
    for i in range(LOOKBACK):
        day_idx = idx - LOOKBACK + 1 + i
        if closes[day_idx - 1] != 0:
            ret = (closes[day_idx] - closes[day_idx - 1]) / closes[day_idx - 1]
            w = i + 1  # 1,2,...,LOOKBACK (recent = higher weight)
            weighted_sum += ret * w
            weight_total += w
    if weight_total == 0:
        return 0.5
    avg_ret = weighted_sum / weight_total
    score = 0.5 + avg_ret * 50.0
    return max(0.0, min(1.0, score))
