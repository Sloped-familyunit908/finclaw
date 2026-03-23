"""
Factor: crypto_elder_bear_power
Description: low - EMA(13) — bear power
Category: crypto
"""

FACTOR_NAME = "crypto_elder_bear_power"
FACTOR_DESC = "low - EMA(13) — bear power"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. <0.5 = bears pushing below EMA, >0.5 = weak bears."""
    period = 13
    if idx < period + 1:
        return 0.5

    mult = 2.0 / (period + 1)
    ema = closes[idx - period - 1]
    for i in range(idx - period, idx):
        ema = closes[i] * mult + ema * (1 - mult)

    bear_power = lows[idx - 1] - ema
    if closes[idx - 1] <= 0:
        return 0.5

    normalized = bear_power / (closes[idx - 1] * 0.05)
    score = 0.5 + normalized * 0.5
    return max(0.0, min(1.0, score))
