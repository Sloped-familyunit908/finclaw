"""
Auto-generated factor: value_momentum
Description: Price below 60-day MA but above 120-day MA (value + long-term momentum)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "value_momentum"
FACTOR_DESC = "Price below 60-day MA but above 120-day MA (value + long-term momentum)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Value momentum: below MA60 but above MA120."""

    if idx < 120:
        return 0.5

    # MA60
    ma60_total = 0.0
    for i in range(idx - 59, idx + 1):
        ma60_total += closes[i]
    ma60 = ma60_total / 60.0

    # MA120
    ma120_total = 0.0
    for i in range(idx - 119, idx + 1):
        ma120_total += closes[i]
    ma120 = ma120_total / 120.0

    price = closes[idx]

    # Below MA60 (short-term value) but above MA120 (long-term uptrend)
    below_ma60 = price < ma60
    above_ma120 = price > ma120

    if below_ma60 and above_ma120:
        # How much below MA60 (more below = more value)
        value_gap = (ma60 - price) / ma60 if ma60 > 0 else 0.0
        # How much above MA120 (more above = stronger trend)
        trend_gap = (price - ma120) / ma120 if ma120 > 0 else 0.0
        score = 0.7 + value_gap * 2.0 + trend_gap
        return max(0.0, min(1.0, score))
    elif above_ma120:
        return 0.55
    else:
        return 0.35
