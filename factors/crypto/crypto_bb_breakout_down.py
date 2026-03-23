"""
Factor: crypto_bb_breakout_down
Description: Price below lower Bollinger Band (oversold)
Category: crypto
"""

FACTOR_NAME = "crypto_bb_breakout_down"
FACTOR_DESC = "Price below lower Bollinger Band (oversold signal)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = more oversold (further below lower BB)."""
    period = 24
    if idx < period:
        return 0.5

    window = closes[idx - period + 1:idx + 1]
    mean = sum(window) / period
    if mean <= 0:
        return 0.5

    variance = sum((x - mean) ** 2 for x in window) / period
    std = variance ** 0.5
    if std <= 0:
        return 0.5

    lower_bb = mean - 2 * std
    price = closes[idx]

    if price >= lower_bb:
        # Above lower band - not oversold
        position = (price - mean) / (2 * std) if std > 0 else 0
        score = max(0.0, 0.3 - position * 0.2)
    else:
        # Below lower band - oversold
        undershoot = (lower_bb - price) / std
        score = 0.5 + min(undershoot / 4.0, 0.5)

    return max(0.0, min(1.0, score))
