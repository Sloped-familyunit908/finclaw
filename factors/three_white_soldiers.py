"""
Auto-generated factor: three_white_soldiers
Description: Three consecutive bullish candles with increasing closes
Category: pattern
Generated: seed
"""

FACTOR_NAME = "three_white_soldiers"
FACTOR_DESC = "Three consecutive bullish candles with increasing closes"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect three white soldiers pattern."""

    if idx < 4:
        return 0.5

    # Three consecutive up closes with increasing closes
    c0 = closes[idx]
    c1 = closes[idx - 1]
    c2 = closes[idx - 2]
    c3 = closes[idx - 3]

    # Each day closes higher than the previous
    increasing = c0 > c1 > c2 > c3

    # Each day is a bullish candle (close > open proxy)
    # Use previous close as open proxy
    bull_0 = c0 > c1  # close > open proxy
    bull_1 = c1 > c2
    bull_2 = c2 > c3

    if increasing and bull_0 and bull_1 and bull_2:
        # Check body sizes are decent
        body_0 = (c0 - c1) / c1 if c1 > 0 else 0.0
        body_1 = (c1 - c2) / c2 if c2 > 0 else 0.0
        body_2 = (c2 - c3) / c3 if c3 > 0 else 0.0

        avg_body = (body_0 + body_1 + body_2) / 3.0
        if avg_body > 0.005:
            return 0.9
        else:
            return 0.7

    # Partial pattern
    if c0 > c1 > c2:
        return 0.6

    return 0.5
