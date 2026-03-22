"""
Factor: morning_star
Description: Three-day morning star pattern (down, small body, up)
Category: candlestick
"""

FACTOR_NAME = "morning_star"
FACTOR_DESC = "Morning star — three-day reversal pattern (down, small body, up)"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Three-day pattern: day1 bearish, day2 small body (star), day3 bullish."""
    if idx < 5:
        return 0.5

    # Day 1 (two days ago): bearish
    day1_close = closes[idx - 2]
    day1_open_proxy = closes[idx - 3]
    day1_bearish = day1_close < day1_open_proxy
    day1_body = abs(day1_close - day1_open_proxy)

    # Day 2 (yesterday): small body (the star)
    day2_close = closes[idx - 1]
    day2_open_proxy = closes[idx - 2]
    day2_body = abs(day2_close - day2_open_proxy)
    day2_range = highs[idx - 1] - lows[idx - 1]
    day2_small = day2_body < day1_body * 0.5 if day1_body > 0 else day2_body < day2_range * 0.3

    # Day 3 (today): bullish
    day3_close = closes[idx]
    day3_open_proxy = closes[idx - 1]
    day3_bullish = day3_close > day3_open_proxy
    day3_body = abs(day3_close - day3_open_proxy)

    if not (day1_bearish and day2_small and day3_bullish):
        return 0.5

    # Stronger if day3 closes above midpoint of day1's body
    midpoint = (day1_close + day1_open_proxy) / 2.0
    strong = day3_close > midpoint

    if strong:
        score = 0.85
    else:
        score = 0.7

    return max(0.0, min(1.0, score))
