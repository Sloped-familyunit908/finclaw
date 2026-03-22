FACTOR_NAME = "kurtosis_20d"
FACTOR_DESC = "Kurtosis of returns over 20 days — high = fat tails = more extreme moves possible"
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
    if var == 0:
        return 0.5
    # Kurtosis = E[(X-μ)⁴] / σ⁴ - 3 (excess kurtosis)
    m4 = sum((r - mean_r) ** 4 for r in rets) / n
    kurt = m4 / (var ** 2) - 3.0
    # High kurtosis with positive recent momentum = bullish potential
    last_ret = rets[-1] if rets else 0
    if last_ret > 0:
        score = 0.5 + min(kurt, 5.0) / 10.0 * 0.5
    else:
        score = 0.5 - min(kurt, 5.0) / 10.0 * 0.3
    return max(0.0, min(1.0, score))
