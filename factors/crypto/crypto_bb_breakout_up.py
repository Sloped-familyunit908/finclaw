"""
Factor: crypto_bb_breakout_up
Description: Price above upper Bollinger Band (breakout signal)
Category: crypto
"""

FACTOR_NAME = "crypto_bb_breakout_up"
FACTOR_DESC = "Price above upper Bollinger Band breakout"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = further above upper BB."""
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

    upper_bb = mean + 2 * std
    price = closes[idx]

    if price <= upper_bb:
        # Below upper band - no breakout
        # Scale: how close to upper band
        if std > 0:
            position = (price - mean) / (2 * std)
            score = max(0.0, 0.3 + position * 0.2)
        else:
            score = 0.3
    else:
        # Above upper band - breakout
        overshoot = (price - upper_bb) / std
        score = 0.5 + min(overshoot / 4.0, 0.5)

    return max(0.0, min(1.0, score))
