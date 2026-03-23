"""
Factor: crypto_bollinger_fast
Description: Position in 12-period Bollinger bands
Category: crypto
"""

FACTOR_NAME = "crypto_bollinger_fast"
FACTOR_DESC = "Position in fast 12-period Bollinger bands — overbought/oversold"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Maps price position within 12-period Bollinger bands."""
    import math

    period = 12
    if idx < period:
        return 0.5

    window = closes[idx - period + 1:idx + 1]
    sma = sum(window) / len(window)
    var = sum((x - sma) ** 2 for x in window) / len(window)
    std = math.sqrt(var) if var > 0 else 0

    if std <= 0:
        return 0.5

    upper = sma + 2 * std
    lower = sma - 2 * std
    band_width = upper - lower

    if band_width <= 0:
        return 0.5

    # Position of price within bands: 0 = at lower band, 1 = at upper band
    position = (closes[idx] - lower) / band_width

    # Clamp to [0, 1] — price can be outside Bollinger bands
    return max(0.0, min(1.0, position))
