"""
Factor: crypto_sortino_proxy
Description: Mean return / downside deviation over 48h
Category: crypto
"""

FACTOR_NAME = "crypto_sortino_proxy"
FACTOR_DESC = "Sortino ratio proxy — penalizes only downside volatility"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = good returns with low downside risk."""
    lookback = 48
    if idx < lookback:
        return 0.5

    returns = []
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i - 1] > 0:
            ret = (closes[i] - closes[i - 1]) / closes[i - 1]
            returns.append(ret)

    if len(returns) < 10:
        return 0.5

    mean_ret = sum(returns) / len(returns)

    # Downside deviation: std of negative returns only
    neg_returns = [r for r in returns if r < 0]
    if len(neg_returns) < 3:
        # Very few negative returns = bullish
        return 0.7

    downside_var = sum(r ** 2 for r in neg_returns) / len(neg_returns)
    downside_dev = downside_var ** 0.5

    if downside_dev <= 0:
        return 0.5

    sortino = mean_ret / downside_dev
    score = 0.5 + sortino * 0.5
    return max(0.0, min(1.0, score))
