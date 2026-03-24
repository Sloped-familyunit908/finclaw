"""
Factor: risk_new_low_60d
Description: Price at new 60-day low — broken trend
Category: risk_warning
"""

FACTOR_NAME = "risk_new_low_60d"
FACTOR_DESC = "Price at new 60-day low — trend broken, no visible support"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Price at or near new 60-day low.
    Trend is broken, no visible support. High risk.
    """
    period = 60
    if idx < period:
        return 0.5

    low_60d = min(lows[idx - period + 1 : idx])  # Previous 60 days (excluding today)

    if low_60d <= 0:
        return 0.5

    # How close is current price to the 60-day low?
    distance = (closes[idx] - low_60d) / low_60d

    if distance > 0.05:
        return 0.5  # More than 5% above 60-day low — not near

    if lows[idx] <= low_60d:
        # New 60-day low — maximum risk
        return 0.95

    # Near the 60-day low
    # 0% distance = 0.9, 5% distance = 0.5
    score = 0.9 - (distance / 0.05) * 0.4

    return max(0.0, min(1.0, score))
