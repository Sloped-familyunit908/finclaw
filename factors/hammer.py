"""
Factor: hammer
Description: Hammer candlestick (small body, long lower shadow, at bottom)
Category: candlestick
"""

FACTOR_NAME = "hammer"
FACTOR_DESC = "Hammer candlestick pattern — small body, long lower shadow, at bottom"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Detect hammer pattern: long lower shadow, small body, near top of range."""
    if idx < 10:
        return 0.5

    high = highs[idx]
    low = lows[idx]
    close = closes[idx]
    prev_close = closes[idx - 1]

    # Use close and prev_close as proxy for open
    body_top = max(close, prev_close)
    body_bottom = min(close, prev_close)
    body_size = body_top - body_bottom
    total_range = high - low

    if total_range <= 0:
        return 0.5

    lower_shadow = body_bottom - low
    upper_shadow = high - body_top

    body_ratio = body_size / total_range
    lower_shadow_ratio = lower_shadow / total_range

    # Hammer: small body (< 30% of range), long lower shadow (> 60% of range)
    is_hammer = body_ratio < 0.35 and lower_shadow_ratio > 0.55 and upper_shadow < body_size * 0.5

    if not is_hammer:
        return 0.5

    # Context: more bullish if at recent low
    recent_low = min(lows[idx - 9:idx + 1])
    if low <= recent_low * 1.02:
        score = 0.85
    else:
        score = 0.7

    return max(0.0, min(1.0, score))
