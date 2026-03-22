"""
Factor: doji
Description: Doji candle (open ≈ close, signals indecision)
Category: candlestick
"""

FACTOR_NAME = "doji"
FACTOR_DESC = "Doji candle — open approximately equals close, signals indecision"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Doji: very small body relative to range. Bullish at support, bearish at resistance."""
    if idx < 10:
        return 0.5

    high = highs[idx]
    low = lows[idx]
    close = closes[idx]
    open_proxy = closes[idx - 1]

    total_range = high - low
    if total_range <= 0:
        return 0.5

    body = abs(close - open_proxy)
    body_ratio = body / total_range

    # Doji when body is < 10% of range
    if body_ratio >= 0.1:
        return 0.5

    # It's a doji — context determines bullish/bearish
    recent_low = min(lows[idx - 9:idx + 1])
    recent_high = max(highs[idx - 9:idx + 1])
    price_range = recent_high - recent_low

    if price_range <= 0:
        return 0.6  # Doji detected but no context

    position = (close - recent_low) / price_range

    if position < 0.3:
        # Doji at bottom = potential reversal = bullish
        score = 0.75
    elif position > 0.7:
        # Doji at top = potential reversal = bearish
        score = 0.3
    else:
        # Doji in middle = indecision
        score = 0.55

    return max(0.0, min(1.0, score))
