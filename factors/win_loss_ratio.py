FACTOR_NAME = "win_loss_ratio"
FACTOR_DESC = "Average winning day return / average losing day return over 20 days"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    win_sum = 0.0
    win_count = 0
    loss_sum = 0.0
    loss_count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i < 1 or closes[i - 1] == 0:
            continue
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        if ret > 0:
            win_sum += ret
            win_count += 1
        elif ret < 0:
            loss_sum += abs(ret)
            loss_count += 1
    if win_count == 0 or loss_count == 0:
        return 0.5
    avg_win = win_sum / win_count
    avg_loss = loss_sum / loss_count
    if avg_loss == 0:
        return 0.8
    ratio = avg_win / avg_loss
    # Map [0, 3] to [0, 1]
    score = ratio / 3.0
    return max(0.0, min(1.0, score))
