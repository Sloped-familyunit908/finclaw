"""
Factor: body_size_ratio
Description: Today's body size vs 10-day average body size (big moves)
Category: candlestick
"""

FACTOR_NAME = "body_size_ratio"
FACTOR_DESC = "Today's body size vs 10-day average — large bullish bodies = strong signal"
FACTOR_CATEGORY = "candlestick"


def compute(closes, highs, lows, volumes, idx):
    """Large bullish body relative to average = strong conviction."""
    if idx < 11:
        return 0.5

    # Today's body
    today_body = closes[idx] - closes[idx - 1]
    today_body_abs = abs(today_body)

    # 10-day average body size
    total_body = 0.0
    for i in range(idx - 10, idx):
        total_body += abs(closes[i] - closes[i - 1])
    avg_body = total_body / 10.0

    if avg_body <= 0:
        return 0.5

    ratio = today_body_abs / avg_body

    # Direction matters
    if today_body > 0:
        # Bullish — large body = more bullish
        if ratio > 2.0:
            score = 0.85
        elif ratio > 1.5:
            score = 0.7
        elif ratio > 1.0:
            score = 0.6
        else:
            score = 0.55
    elif today_body < 0:
        # Bearish — large body = more bearish
        if ratio > 2.0:
            score = 0.15
        elif ratio > 1.5:
            score = 0.3
        elif ratio > 1.0:
            score = 0.4
        else:
            score = 0.45
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
