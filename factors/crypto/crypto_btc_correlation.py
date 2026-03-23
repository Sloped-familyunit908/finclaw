"""
Factor: crypto_btc_correlation
Description: Rolling 48h correlation with first stock (BTC proxy)
Category: crypto
"""

FACTOR_NAME = "crypto_btc_correlation"
FACTOR_DESC = "Rolling 48h correlation with BTC proxy — decorrelation signals alpha"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Returns float in [0, 1]. 
    This is a single-asset factor. Without multi-asset data, approximates
    by checking auto-correlation of returns at different lags.
    High = trending (correlated with recent self), Low = mean-reverting.
    """
    import math

    lookback = 48
    if idx < lookback:
        return 0.5

    # Compute returns
    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)

    if len(returns) < 20:
        return 0.5

    # Auto-correlation at lag 1 (proxy for trending vs mean-reverting)
    n = len(returns)
    mean_r = sum(returns) / n
    var = sum((r - mean_r) ** 2 for r in returns) / n
    if var <= 0:
        return 0.5

    cov = sum((returns[i] - mean_r) * (returns[i - 1] - mean_r) for i in range(1, n)) / (n - 1)
    autocorr = cov / var

    # autocorr > 0: trending (momentum), < 0: mean-reverting
    # Map [-1, 1] → [0, 1]
    score = (autocorr + 1.0) / 2.0

    return max(0.0, min(1.0, score))
