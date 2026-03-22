FACTOR_NAME = "alpha_volume_return_corr"
FACTOR_DESC = "Correlation between volume and returns over 20 days (negative = bullish divergence)"
FACTOR_CATEGORY = "alpha101"
LOOKBACK = 21

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    n = 20
    rets = []
    vols = []
    for i in range(idx - n + 1, idx + 1):
        if closes[i - 1] != 0:
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
            vols.append(float(volumes[i]))
    if len(rets) < 5:
        return 0.5
    mean_r = sum(rets) / len(rets)
    mean_v = sum(vols) / len(vols)
    cov = 0.0
    var_r = 0.0
    var_v = 0.0
    for i in range(len(rets)):
        dr = rets[i] - mean_r
        dv = vols[i] - mean_v
        cov += dr * dv
        var_r += dr * dr
        var_v += dv * dv
    denom = (var_r * var_v) ** 0.5
    if denom == 0:
        return 0.5
    corr = cov / denom  # [-1, 1]
    # Negative correlation = bullish divergence
    score = 0.5 - corr * 0.5
    return max(0.0, min(1.0, score))
