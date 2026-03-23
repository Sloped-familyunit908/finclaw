"""
Factor: crypto_volatility_regime
Description: Rolling 48h realized volatility regime detection
Category: crypto
"""

FACTOR_NAME = "crypto_volatility_regime"
FACTOR_DESC = "Volatility regime — low vol signals breakout coming, high vol signals mean reversion"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Computes rolling 48h realized volatility and compares to longer-term average.
    Low volatility relative to norm → breakout expected → slightly bullish (0.6)
    High volatility → mean reversion likely → neutral-to-cautious (0.4)
    
    Uses log returns for proper volatility calculation.
    """
    short_window = 48
    long_window = 168  # 7 days
    if idx < long_window:
        return 0.5

    import math

    # Short-term realized vol (48h)
    returns_short = []
    for i in range(idx - short_window + 1, idx + 1):
        if closes[i - 1] > 0 and closes[i] > 0:
            returns_short.append(math.log(closes[i] / closes[i - 1]))

    if len(returns_short) < 10:
        return 0.5

    mean_r = sum(returns_short) / len(returns_short)
    var_short = sum((r - mean_r) ** 2 for r in returns_short) / len(returns_short)
    vol_short = math.sqrt(var_short) if var_short > 0 else 0

    # Long-term realized vol (168h)
    returns_long = []
    for i in range(idx - long_window + 1, idx + 1):
        if closes[i - 1] > 0 and closes[i] > 0:
            returns_long.append(math.log(closes[i] / closes[i - 1]))

    if len(returns_long) < 10:
        return 0.5

    mean_rl = sum(returns_long) / len(returns_long)
    var_long = sum((r - mean_rl) ** 2 for r in returns_long) / len(returns_long)
    vol_long = math.sqrt(var_long) if var_long > 0 else 0

    if vol_long <= 0:
        return 0.5

    # Ratio: <1 means low-vol regime, >1 means high-vol regime
    vol_ratio = vol_short / vol_long

    # Low vol (ratio < 0.7) → breakout coming → score ~0.65
    # Normal vol (ratio ~ 1.0) → score 0.5
    # High vol (ratio > 1.5) → mean reversion → score ~0.35
    score = 0.5 + (1.0 - vol_ratio) * 0.3
    return max(0.0, min(1.0, score))
