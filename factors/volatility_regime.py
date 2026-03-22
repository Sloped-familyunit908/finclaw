"""
Auto-generated factor: volatility_regime
Description: Volatility regime detector — low vol with uptrend = bullish, high vol with downtrend = bearish
Category: volatility
Generated: seed
"""

FACTOR_NAME = "volatility_regime"
FACTOR_DESC = "Volatility regime detector — low vol with uptrend = bullish, high vol with downtrend = bearish"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Compare 20-day vol to 60-day vol, combined with price vs MA20."""

    if idx < 60:
        return 0.5

    # Daily returns for last 60 days
    returns_60 = []
    for i in range(idx - 59, idx + 1):
        if closes[i - 1] <= 0:
            returns_60.append(0.0)
        else:
            returns_60.append((closes[i] - closes[i - 1]) / closes[i - 1])

    # 20-day realized vol (last 20 returns)
    ret_20 = returns_60[-20:]
    mean_20 = sum(ret_20) / 20.0
    var_20 = sum((r - mean_20) ** 2 for r in ret_20) / 20.0
    vol_20 = var_20 ** 0.5

    # 60-day realized vol
    mean_60 = sum(returns_60) / 60.0
    var_60 = sum((r - mean_60) ** 2 for r in returns_60) / 60.0
    vol_60 = var_60 ** 0.5

    # MA20
    ma20 = sum(closes[idx - 19:idx + 1]) / 20.0

    # Vol ratio component: vol_20 < vol_60 → calming down → positive
    if vol_60 <= 0:
        vol_score = 0.5
    else:
        vol_ratio = vol_20 / vol_60
        # ratio < 1 (calming) → high score; ratio > 1 (heating) → low score
        vol_score = 1.0 - min(vol_ratio, 2.0) / 2.0

    # Trend component: price above MA20 → bullish
    if ma20 <= 0:
        trend_score = 0.5
    else:
        pct_above = (closes[idx] - ma20) / ma20
        # -5% to +5% maps to 0 to 1
        trend_score = (pct_above + 0.05) / 0.10

    trend_score = max(0.0, min(1.0, trend_score))

    # Combine: 50% vol regime + 50% trend
    score = 0.5 * vol_score + 0.5 * trend_score
    return max(0.0, min(1.0, score))
