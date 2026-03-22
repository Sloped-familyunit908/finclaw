FACTOR_NAME = "recent_vs_old_return"
FACTOR_DESC = "Last 10-day return / Previous 10-day return — acceleration or deceleration"
FACTOR_CATEGORY = "relative_performance"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    if closes[idx - 10] == 0 or closes[idx - 20] == 0:
        return 0.5
    recent_ret = (closes[idx] - closes[idx - 10]) / closes[idx - 10]
    old_ret = (closes[idx - 10] - closes[idx - 20]) / closes[idx - 20]
    if abs(old_ret) < 0.001:
        # Old return near zero
        if recent_ret > 0:
            return 0.7
        elif recent_ret < 0:
            return 0.3
        return 0.5
    ratio = recent_ret / abs(old_ret)
    score = 0.5 + ratio * 0.2
    return max(0.0, min(1.0, score))
