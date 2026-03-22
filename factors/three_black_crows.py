"""
Auto-generated factor: three_black_crows
Description: Three consecutive bearish candles (bearish, low score)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "three_black_crows"
FACTOR_DESC = "Three consecutive bearish candles (bearish, low score)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect three black crows pattern (bearish)."""

    if idx < 4:
        return 0.5

    c0 = closes[idx]
    c1 = closes[idx - 1]
    c2 = closes[idx - 2]
    c3 = closes[idx - 3]

    # Each day closes lower than the previous
    decreasing = c0 < c1 < c2 < c3

    # Each day is bearish
    bear_0 = c0 < c1
    bear_1 = c1 < c2
    bear_2 = c2 < c3

    if decreasing and bear_0 and bear_1 and bear_2:
        body_0 = abs(c0 - c1) / c1 if c1 > 0 else 0.0
        body_1 = abs(c1 - c2) / c2 if c2 > 0 else 0.0
        body_2 = abs(c2 - c3) / c3 if c3 > 0 else 0.0

        avg_body = (body_0 + body_1 + body_2) / 3.0
        if avg_body > 0.005:
            return 0.1  # Strong bearish
        else:
            return 0.3

    # Partial pattern
    if c0 < c1 < c2:
        return 0.4

    return 0.5
