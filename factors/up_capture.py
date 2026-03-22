FACTOR_NAME = "up_capture"
FACTOR_DESC = "Average return on up days / average abs return on down days — up capture ratio"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    up_sum = 0.0
    up_count = 0
    down_sum = 0.0
    down_count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        if ret > 0:
            up_sum += ret
            up_count += 1
        elif ret < 0:
            down_sum += abs(ret)
            down_count += 1
    if up_count == 0 or down_count == 0:
        return 0.5
    avg_up = up_sum / up_count
    avg_down = down_sum / down_count
    if avg_down == 0:
        return 0.8
    ratio = avg_up / avg_down  # >1 = bigger up moves
    # Map [0, 3] to [0, 1]
    score = ratio / 3.0
    return max(0.0, min(1.0, score))
