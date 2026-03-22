"""
Factor: support_bounce
Description: Price bouncing off recent support (lowest low of last 20 days)
Category: support_resistance
"""

FACTOR_NAME = "support_bounce"
FACTOR_DESC = "Price bouncing off 20-day support — recovery from lows"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Detect price touching support and bouncing up."""
    lookback = 20
    if idx < lookback + 1:
        return 0.5

    # Support = lowest low in lookback period
    support = min(lows[idx - lookback:idx])
    if support <= 0:
        return 0.5

    price = closes[idx]
    today_low = lows[idx]

    # Check if today's low touched or was near support
    distance_to_support = (today_low - support) / support if support > 0 else 1.0
    near_support = distance_to_support < 0.02

    # Check if bouncing (close above low significantly)
    day_range = highs[idx] - lows[idx]
    if day_range > 0:
        bounce_strength = (price - today_low) / day_range
    else:
        bounce_strength = 0.5

    if near_support and bounce_strength > 0.6:
        # Touched support and bounced strongly
        score = 0.8
    elif near_support and bounce_strength > 0.4:
        # Near support with moderate bounce
        score = 0.7
    elif near_support:
        # At support but weak bounce
        score = 0.55
    elif price < support:
        # Below support (broken)
        score = 0.3
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
