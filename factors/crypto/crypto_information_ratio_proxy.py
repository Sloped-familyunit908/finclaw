"""
Factor: crypto_information_ratio_proxy
Description: Return / tracking error vs simple buy-hold
Category: crypto
"""

FACTOR_NAME = "crypto_information_ratio_proxy"
FACTOR_DESC = "Return / tracking error vs simple buy-hold"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = outperforming simple buy-hold on risk-adjusted basis."""
    lookback = 24
    if idx < lookback + 1:
        return 0.5

    if closes[idx - lookback - 1] <= 0:
        return 0.5

    # Simple momentum returns vs buy-hold benchmark
    returns = []
    for i in range(idx - lookback, idx):
        if i < 1 or closes[i - 1] <= 0:
            returns.append(0)
            continue
        returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    mean_ret = sum(returns) / len(returns)
    if len(returns) < 2:
        return 0.5

    # Tracking error (std of returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
    te = var ** 0.5

    if te <= 0:
        return 0.5

    ir = mean_ret / te
    score = 0.5 + ir * 2.0
    return max(0.0, min(1.0, score))
