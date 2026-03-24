"""
Factor: risk_limit_down_nearby
Description: Price within 2% of daily limit-down — danger zone
Category: risk_warning
"""

FACTOR_NAME = "risk_limit_down_nearby"
FACTOR_DESC = "Price within 2% of daily limit-down — danger of being locked in"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Price within 2% of daily limit-down.
    For A-shares, limit-down is -10% from previous close.
    When price is near limit-down, there's danger of being locked in
    (unable to sell).
    """
    if idx < 1:
        return 0.5

    prev_close = closes[idx - 1]
    if prev_close <= 0:
        return 0.5

    # Daily limit-down level (A-shares: -10%)
    limit_down = prev_close * 0.90

    # How far is current price from limit-down
    if limit_down <= 0:
        return 0.5

    distance_to_limit = (closes[idx] - limit_down) / prev_close

    if distance_to_limit > 0.05:
        return 0.5  # Far from limit-down — safe

    if distance_to_limit <= 0:
        # AT or BELOW limit-down — maximum danger
        return 1.0

    # Within 5% of limit-down — increasing danger
    # 5% away = 0.5, 0% away = 1.0
    score = 1.0 - (distance_to_limit / 0.05)
    score = 0.6 + 0.4 * score

    return max(0.0, min(1.0, score))
