"""
Factor: realized_vol_10d
Description: 10-day realized volatility (annualized)
Category: volatility
"""

FACTOR_NAME = "realized_vol_10d"
FACTOR_DESC = "10-day realized volatility — annualized standard deviation of returns"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """10-day realized vol. Low vol = calm (score ~0.5), high vol context-dependent."""
    period = 10
    if idx < period + 1:
        return 0.5

    # Calculate daily returns
    returns = []
    for i in range(idx - period + 1, idx + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

    if len(returns) < 2:
        return 0.5

    # Mean
    mean_ret = sum(returns) / len(returns)

    # Variance
    variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)

    # Annualized vol (sqrt(252) ≈ 15.87)
    ann_vol = (variance ** 0.5) * 15.87

    # Low vol might precede breakout (slightly bullish), extreme vol = uncertainty
    # 10% annual vol = calm, 30% = normal, 60%+ = extreme
    # Map: low vol = 0.6 (bullish calm), normal = 0.5, extreme = 0.35
    if ann_vol < 0.15:
        score = 0.65
    elif ann_vol < 0.30:
        score = 0.55
    elif ann_vol < 0.50:
        score = 0.45
    else:
        score = 0.35

    return max(0.0, min(1.0, score))
