"""
Factor: crypto_regime_trend_strength
Description: Abs(EMA slope) normalized (0=range, 1=strong trend)
Category: crypto
"""

FACTOR_NAME = "crypto_regime_trend_strength"
FACTOR_DESC = "Abs(EMA slope) normalized (0=range, 1=strong trend)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong trending regime."""
    period = 24
    if idx < period + 2:
        return 0.5

    mult = 2.0 / (period + 1)

    ema_now = closes[idx - period - 2]
    for i in range(idx - period - 1, idx):
        ema_now = closes[i] * mult + ema_now * (1 - mult)

    ema_prev = closes[idx - period - 2]
    for i in range(idx - period - 1, idx - 1):
        ema_prev = closes[i] * mult + ema_prev * (1 - mult)

    if closes[idx - 1] <= 0:
        return 0.5

    slope = abs(ema_now - ema_prev) / closes[idx - 1]
    score = min(slope * 200.0, 1.0)
    return max(0.0, min(1.0, score))
