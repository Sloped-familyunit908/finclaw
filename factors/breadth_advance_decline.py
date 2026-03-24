"""
Factor: breadth_advance_decline
Description: Estimated advance/decline ratio from price data
Category: market_breadth
"""

FACTOR_NAME = "breadth_advance_decline"
FACTOR_DESC = "Advance/decline ratio — fraction of positive stocks estimated from price"
FACTOR_CATEGORY = "market_breadth"


def compute(closes, highs, lows, volumes, idx):
    """Estimated advance/decline from the single stock's price data.
    Since we only have one stock, we proxy breadth by looking at
    the ratio of up days vs down days over recent history.
    More up days = "advancing market" environment.
    """
    lookback = 20
    if idx < lookback:
        return 0.5

    up_days = 0
    down_days = 0

    for i in range(idx - lookback + 1, idx + 1):
        if i == 0:
            continue
        if closes[i] > closes[i - 1]:
            up_days += 1
        elif closes[i] < closes[i - 1]:
            down_days += 1

    total = up_days + down_days
    if total == 0:
        return 0.5

    # Advance/decline ratio mapped to [0, 1]
    ad_ratio = up_days / total

    return max(0.0, min(1.0, ad_ratio))
