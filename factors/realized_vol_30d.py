"""
Factor: realized_vol_30d
Description: 30-day realized volatility (annualized)
Category: volatility
"""

FACTOR_NAME = "realized_vol_30d"
FACTOR_DESC = "30-day realized volatility — longer-term volatility measure"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """30-day realized vol."""
    period = 30
    if idx < period + 1:
        return 0.5

    returns = []
    for i in range(idx - period + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 2:
        return 0.5

    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    ann_vol = (variance ** 0.5) * 15.87

    if ann_vol < 0.15:
        score = 0.65
    elif ann_vol < 0.30:
        score = 0.55
    elif ann_vol < 0.50:
        score = 0.45
    else:
        score = 0.35

    return max(0.0, min(1.0, score))
