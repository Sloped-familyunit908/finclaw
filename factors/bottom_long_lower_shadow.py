"""
Factor: bottom_long_lower_shadow
Description: Detects long lower shadow (hammer) candles signaling price defense
Category: bottom_confirmation
"""

FACTOR_NAME = "bottom_long_lower_shadow"
FACTOR_DESC = "Long lower shadow candle — someone is defending this price level"
FACTOR_CATEGORY = "bottom_confirmation"


def compute(closes, highs, lows, volumes, idx):
    """Detect bullish hammer: lower shadow > 2x body AND close > open (proxy).

    A long lower shadow means sellers pushed price down but buyers fought back.
    Stronger signal when it occurs near recent lows.
    """
    if idx < 5:
        return 0.5

    high = highs[idx]
    low = lows[idx]
    close = closes[idx]
    prev_close = closes[idx - 1]

    # Use close vs prev_close as open proxy
    open_proxy = prev_close
    body_top = max(close, open_proxy)
    body_bottom = min(close, open_proxy)
    body_size = body_top - body_bottom

    total_range = high - low
    if total_range <= 0:
        return 0.5

    lower_shadow = body_bottom - low
    upper_shadow = high - body_top

    # Body can be zero (doji-hammer) — use a small minimum for ratio
    effective_body = max(body_size, total_range * 0.01)

    # Core condition: long lower shadow >= 2x body AND bullish close
    # Also require lower shadow to be >= 40% of total range
    # to avoid false positives on flat/narrow-range candles
    is_bullish = close > open_proxy
    has_long_lower_shadow = (lower_shadow >= 2.0 * effective_body
                             and lower_shadow >= total_range * 0.4)

    if not has_long_lower_shadow:
        return 0.5

    if not is_bullish:
        # Bearish hammer (hanging man) — less reliable as bottom signal
        return 0.55

    # Score based on shadow strength
    shadow_ratio = lower_shadow / effective_body
    if shadow_ratio > 4.0:
        base_score = 1.0
    elif shadow_ratio > 3.0:
        base_score = 0.9
    else:
        base_score = 0.8

    # Bonus: at or near recent low (stronger bottom signal)
    lookback = min(20, idx)
    recent_low = min(lows[idx - lookback:idx + 1])
    if low <= recent_low * 1.01:
        base_score = min(1.0, base_score + 0.1)

    # Penalty: upper shadow is large (less clean hammer)
    if upper_shadow > body_size * 0.5:
        base_score -= 0.1

    return max(0.0, min(1.0, base_score))
