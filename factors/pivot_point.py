"""
Factor: pivot_point
Description: Classic pivot point: (H+L+C)/3, score based on price vs pivot
Category: support_resistance
"""

FACTOR_NAME = "pivot_point"
FACTOR_DESC = "Classic pivot point — price position relative to (H+L+C)/3"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Classic pivot: PP = (H+L+C)/3 from yesterday. Above = bullish."""
    if idx < 2:
        return 0.5

    # Yesterday's data for pivot calculation
    prev_high = highs[idx - 1]
    prev_low = lows[idx - 1]
    prev_close = closes[idx - 1]

    pivot = (prev_high + prev_low + prev_close) / 3.0

    # Support and resistance levels
    r1 = 2.0 * pivot - prev_low
    s1 = 2.0 * pivot - prev_high
    r2 = pivot + (prev_high - prev_low)
    s2 = pivot - (prev_high - prev_low)

    price = closes[idx]

    # Score based on position relative to pivot levels
    if price >= r2:
        score = 0.9
    elif price >= r1:
        # Between R1 and R2
        if r2 > r1:
            score = 0.7 + 0.2 * (price - r1) / (r2 - r1)
        else:
            score = 0.8
    elif price >= pivot:
        # Between pivot and R1
        if r1 > pivot:
            score = 0.5 + 0.2 * (price - pivot) / (r1 - pivot)
        else:
            score = 0.6
    elif price >= s1:
        # Between S1 and pivot
        if pivot > s1:
            score = 0.3 + 0.2 * (price - s1) / (pivot - s1)
        else:
            score = 0.4
    elif price >= s2:
        # Between S2 and S1
        if s1 > s2:
            score = 0.15 + 0.15 * (price - s2) / (s1 - s2)
        else:
            score = 0.2
    else:
        score = 0.1

    return max(0.0, min(1.0, score))
