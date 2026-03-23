"""
Factor: crypto_inside_bar_breakout
Description: Inside bar followed by range breakout
Category: crypto
"""

FACTOR_NAME = "crypto_inside_bar_breakout"
FACTOR_DESC = "Inside bar breakout pattern — compression then expansion"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = bullish breakout from inside bar, Low = bearish."""
    if idx < 24:
        return 0.5

    # Check if previous bar was an inside bar (contained within bar before it)
    if idx < 3:
        return 0.5

    mother_high = highs[idx - 2]
    mother_low = lows[idx - 2]
    inside_high = highs[idx - 1]
    inside_low = lows[idx - 1]

    # Inside bar: completely within mother bar
    is_inside = inside_high <= mother_high and inside_low >= mother_low

    if not is_inside:
        return 0.5

    # Current bar breaks out
    if closes[idx] > mother_high:
        # Bullish breakout
        if mother_high - mother_low > 0:
            breakout_strength = (closes[idx] - mother_high) / (mother_high - mother_low)
            score = 0.5 + min(breakout_strength, 1.0) * 0.4
            return max(0.0, min(1.0, score))
    elif closes[idx] < mother_low:
        # Bearish breakout
        if mother_high - mother_low > 0:
            breakout_strength = (mother_low - closes[idx]) / (mother_high - mother_low)
            score = 0.5 - min(breakout_strength, 1.0) * 0.4
            return max(0.0, min(1.0, score))

    return 0.5
