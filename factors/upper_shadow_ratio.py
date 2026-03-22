"""
Factor: upper_shadow_ratio
Description: Upper shadow length vs body (selling pressure at top)
Category: candlestick
"""

FACTOR_NAME = "upper_shadow_ratio"
FACTOR_DESC = "Upper shadow ratio — selling pressure at the top of the candle"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Long upper shadow = selling pressure = bearish. Score inverted."""
    if idx < 1:
        return 0.5

    high = highs[idx]
    low = lows[idx]
    close = closes[idx]
    open_proxy = closes[idx - 1]

    body_top = max(close, open_proxy)
    total_range = high - low

    if total_range <= 0:
        return 0.5

    upper_shadow = high - body_top
    upper_ratio = upper_shadow / total_range

    # Long upper shadow = bearish (score lower)
    # No upper shadow = no selling pressure (neutral to bullish)
    # Ratio > 0.6 = very bearish, < 0.1 = neutral
    score = 0.5 - upper_ratio * 0.6

    return max(0.0, min(1.0, score))
