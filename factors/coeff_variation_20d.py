FACTOR_NAME = "coeff_variation_20d"
FACTOR_DESC = "Coefficient of variation of returns (std/|mean|) — consistency of returns"
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
    if abs(mean_r) < 1e-8:
        return 0.5
    cv = std / abs(mean_r)
    # Low CV + positive mean = consistent positive returns = bullish
    # High CV = inconsistent
    if mean_r > 0:
        # Lower CV is better for positive returns
        score = 0.5 + max(0, 1.0 - cv / 10.0) * 0.4
    else:
        # Negative mean returns, low CV = consistently negative = bearish
        score = 0.5 - max(0, 1.0 - cv / 10.0) * 0.4
    return max(0.0, min(1.0, score))
