FACTOR_NAME = "skewness_20d"
FACTOR_DESC = "Skewness of returns over 20 days — positive skew = more upside potential"
FACTOR_CATEGORY = "statistical"
LOOKBACK = 20

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
    var = sum((r - mean_r) ** 2 for r in rets) / n
    std = var ** 0.5
    if std == 0:
        return 0.5
    # Skewness = E[(X-μ)³] / σ³
    m3 = sum((r - mean_r) ** 3 for r in rets) / n
    skew = m3 / (std ** 3)
    # Positive skew = bullish (right tail). Map [-3, 3] to [0, 1]
    score = 0.5 + skew / 6.0
    return max(0.0, min(1.0, score))
