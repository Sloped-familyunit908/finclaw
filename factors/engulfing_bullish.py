"""
Factor: engulfing_bullish
Description: Bullish engulfing pattern
Category: candlestick
"""

FACTOR_NAME = "engulfing_bullish"
FACTOR_DESC = "Bullish engulfing pattern — today covers yesterday's bearish body"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Today's bullish body completely covers yesterday's bearish body."""
    if idx < 5:
        return 0.5

    today_close = closes[idx]
    today_open_proxy = closes[idx - 1]  # Use prev close as open proxy
    yesterday_close = closes[idx - 1]
    yesterday_open_proxy = closes[idx - 2]

    # Yesterday was bearish (close < open)
    yesterday_bearish = yesterday_close < yesterday_open_proxy

    # Today is bullish (close > open proxy)
    today_bullish = today_close > today_open_proxy

    if not (yesterday_bearish and today_bullish):
        return 0.5

    # Today's body covers yesterday's body
    today_body_top = today_close
    today_body_bottom = today_open_proxy
    yesterday_body_top = yesterday_open_proxy
    yesterday_body_bottom = yesterday_close

    engulfing = today_body_top > yesterday_body_top and today_body_bottom <= yesterday_body_bottom

    if not engulfing:
        return 0.5

    # Context: more powerful at bottom
    recent_low = min(lows[idx - 4:idx + 1])
    at_bottom = lows[idx] <= recent_low * 1.03

    if at_bottom:
        score = 0.85
    else:
        score = 0.7

    return max(0.0, min(1.0, score))
