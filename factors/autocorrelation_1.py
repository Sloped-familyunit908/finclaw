FACTOR_NAME = "autocorrelation_1"
FACTOR_DESC = "Lag-1 autocorrelation of returns — positive = trending, negative = reverting"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 21

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    rets = []
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i > 0 and closes[i - 1] != 0:
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(rets) < 5:
        return 0.5
    n = len(rets)
    mean_r = sum(rets) / n
    # Autocorrelation at lag 1
    num = 0.0
    den = 0.0
    for i in range(n):
        den += (rets[i] - mean_r) ** 2
    for i in range(1, n):
        num += (rets[i] - mean_r) * (rets[i - 1] - mean_r)
    if den == 0:
        return 0.5
    ac = num / den  # [-1, 1]
    # Positive AC + positive recent return = trending up = bullish
    # Negative AC + negative recent return = will revert up = bullish
    last_ret = rets[-1] if rets else 0
    if ac > 0 and last_ret > 0:
        score = 0.5 + ac * 0.3
    elif ac < 0 and last_ret < 0:
        score = 0.5 + abs(ac) * 0.3  # Will revert up
    elif ac > 0 and last_ret < 0:
        score = 0.5 - ac * 0.3  # Trending down
    else:
        score = 0.5
    return max(0.0, min(1.0, score))
