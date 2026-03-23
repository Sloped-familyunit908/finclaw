"""
Factor: crypto_zscore_48h
Description: Z-score of price vs 48h distribution
Category: crypto
"""

FACTOR_NAME = "crypto_zscore_48h"
FACTOR_DESC = "Z-score of price vs 48h distribution — extreme deviation signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = price well above mean, Low = well below."""
    import math

    lookback = 48
    if idx < lookback:
        return 0.5

    window = closes[idx - lookback:idx + 1]
    mean = sum(window) / len(window)
    var = sum((x - mean) ** 2 for x in window) / len(window)
    std = math.sqrt(var) if var > 0 else 0

    if std <= 0:
        return 0.5

    zscore = (closes[idx] - mean) / std

    # Map z-score: -3 → 0 (oversold, mean reversion buy), +3 → 1 (overbought)
    # For mean reversion: extreme low z = bullish, extreme high z = bearish
    # But to keep directional consistency, map directly
    score = 0.5 + zscore / 6.0

    return max(0.0, min(1.0, score))
