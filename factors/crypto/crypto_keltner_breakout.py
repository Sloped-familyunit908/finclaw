"""
Factor: crypto_keltner_breakout
Description: Price outside Keltner bands
Category: crypto
"""

FACTOR_NAME = "crypto_keltner_breakout"
FACTOR_DESC = "Price outside Keltner bands"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.7 = above upper band, <0.3 = below lower band."""
    period = 20
    atr_mult = 2.0
    if idx < period + 1:
        return 0.5

    mult = 2.0 / (period + 1)
    ema = closes[idx - period - 1]
    for i in range(idx - period, idx):
        ema = closes[i] * mult + ema * (1 - mult)

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
    price = closes[idx - 1]

    if price > upper:
        excess = (price - upper) / atr if atr > 0 else 0
        score = 0.7 + min(excess * 0.15, 0.3)
    elif price < lower:
        excess = (lower - price) / atr if atr > 0 else 0
        score = 0.3 - min(excess * 0.15, 0.3)
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
