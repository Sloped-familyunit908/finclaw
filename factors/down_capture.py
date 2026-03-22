FACTOR_NAME = "down_capture"
FACTOR_DESC = "Average return on down days — less negative means better downside protection (bullish)"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    down_sum = 0.0
    down_count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        if ret < 0:
            down_sum += ret
            down_count += 1
    if down_count == 0:
        return 0.8  # No down days = bullish
    avg_down = down_sum / down_count  # negative number
    # Less negative = better. Map [-0.05, 0] to [0, 1]
    score = 1.0 + avg_down * 20.0
    return max(0.0, min(1.0, score))
