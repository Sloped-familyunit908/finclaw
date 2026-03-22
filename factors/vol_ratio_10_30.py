"""
Factor: vol_ratio_10_30
Description: Ratio of 10d vol to 30d vol (increasing = heating up)
Category: volatility
"""

FACTOR_NAME = "vol_ratio_10_30"
FACTOR_DESC = "Volatility ratio 10d/30d — rising short-term vol = heating up"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Ratio of 10-day to 30-day realized volatility."""
    if idx < 31:
        return 0.5

    def calc_vol(start_idx, period):
        returns = []
        for i in range(start_idx - period + 1, start_idx + 1):
            if closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        if len(returns) < 2:
            return 0.0
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        return var ** 0.5

    vol_10 = calc_vol(idx, 10)
    vol_30 = calc_vol(idx, 30)

    if vol_30 <= 0:
        return 0.5

    ratio = vol_10 / vol_30

    # Ratio < 0.8 = vol contracting (potential breakout, slightly bullish)
    # Ratio ≈ 1.0 = stable
    # Ratio > 1.5 = vol expanding rapidly
    if ratio < 0.7:
        score = 0.7  # Squeeze forming
    elif ratio < 1.0:
        score = 0.6
    elif ratio < 1.3:
        score = 0.5
    elif ratio < 1.8:
        score = 0.4
    else:
        score = 0.3  # Very elevated short-term vol

    return max(0.0, min(1.0, score))
