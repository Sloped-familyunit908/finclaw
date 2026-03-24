"""
Factor: top_consecutive_upper_shadow
Description: 3+ consecutive candles with long upper shadows — rejection at highs
Category: top_escape
"""

FACTOR_NAME = "top_consecutive_upper_shadow"
FACTOR_DESC = "3+ bars with upper shadow >2x body — sellers rejecting higher prices"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """3+ consecutive candles with long upper shadows (>2x body).
    Sellers are rejecting higher prices repeatedly — distribution.
    """
    if idx < 3:
        return 0.5

    # Count consecutive candles with long upper shadows
    consecutive = 0
    for i in range(idx, max(idx - 10, 0), -1):
        # Approximate open from previous close
        if i > 0:
            approx_open = closes[i - 1]
        else:
            approx_open = closes[i]

        body = abs(closes[i] - approx_open)
        upper_shadow = highs[i] - max(closes[i], approx_open)

        if upper_shadow <= 0:
            break

        # Upper shadow should be > 2x body for strong rejection
        if body > 0 and upper_shadow >= body * 1.5:
            consecutive += 1
        elif body == 0 and upper_shadow > 0:
            # Doji with upper shadow counts
            consecutive += 1
        else:
            break

    if consecutive < 2:
        return 0.5

    # Also check if near recent highs (within 5% of 20-day high)
    near_high_bonus = 0.0
    if idx >= 20:
        high_20d = max(highs[idx - 19 : idx + 1])
        if high_20d > 0 and closes[idx] / high_20d > 0.95:
            near_high_bonus = 0.1

    if consecutive >= 5:
        base = 0.9
    elif consecutive >= 4:
        base = 0.85
    elif consecutive >= 3:
        base = 0.75
    else:  # 2
        base = 0.65

    score = base + near_high_bonus

    return max(0.0, min(1.0, score))
