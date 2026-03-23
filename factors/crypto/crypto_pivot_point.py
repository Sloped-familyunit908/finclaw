"""
Factor: crypto_pivot_point
Description: Classic pivot point: (H+L+C)/3
Category: crypto
"""

FACTOR_NAME = "crypto_pivot_point"
FACTOR_DESC = "Price position relative to classic pivot point"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = price above pivot (bullish)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Use previous period H/L/C for pivot
    period_high = max(highs[idx - lookback:idx])
    period_low = min(lows[idx - lookback:idx])
    period_close = closes[idx - 1]

    pivot = (period_high + period_low + period_close) / 3.0
    if pivot <= 0:
        return 0.5

    r1 = 2 * pivot - period_low
    s1 = 2 * pivot - period_high

    price = closes[idx]
    pivot_range = r1 - s1
    if pivot_range <= 0:
        return 0.5

    # Position within S1 to R1
    position = (price - s1) / pivot_range
    return max(0.0, min(1.0, position))
