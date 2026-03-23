"""
Factor: crypto_keltner_position
Description: Price position within Keltner channel
Category: crypto
"""

FACTOR_NAME = "crypto_keltner_position"
FACTOR_DESC = "Price position within Keltner channel"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 1.0 = at upper band, 0.0 = at lower band."""
    period = 20
    atr_mult = 2.0
    if idx < period + 1:
        return 0.5

    # EMA
    mult = 2.0 / (period + 1)
    ema = closes[idx - period - 1]
    for i in range(idx - period, idx):
        ema = closes[i] * mult + ema * (1 - mult)

    # ATR
    atr_sum = 0.0
    for i in range(idx - period, idx):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]) if i > 0 else highs[i] - lows[i],
            abs(lows[i] - closes[i - 1]) if i > 0 else highs[i] - lows[i],
        )
        atr_sum += tr
    atr = atr_sum / period

    upper = ema + atr_mult * atr
    lower = ema - atr_mult * atr
    width = upper - lower
    if width <= 0:
        return 0.5

    position = (closes[idx - 1] - lower) / width
    return max(0.0, min(1.0, position))
