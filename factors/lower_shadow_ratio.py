"""
Factor: lower_shadow_ratio
Description: Lower shadow length vs body (buying pressure at bottom)
Category: candlestick
"""

FACTOR_NAME = "lower_shadow_ratio"
FACTOR_DESC = "Lower shadow ratio — buying pressure at the bottom of the candle"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Long lower shadow = buying pressure = bullish."""
    if idx < 1:
        return 0.5

    high = highs[idx]
    low = lows[idx]
    close = closes[idx]
    open_proxy = closes[idx - 1]

    body_bottom = min(close, open_proxy)
    total_range = high - low

    if total_range <= 0:
        return 0.5

    lower_shadow = body_bottom - low
    lower_ratio = lower_shadow / total_range

    # Long lower shadow = bullish (score higher)
    # Ratio > 0.6 = strong buying, < 0.1 = weak
    score = 0.5 + lower_ratio * 0.6

    return max(0.0, min(1.0, score))
