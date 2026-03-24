"""
Factor: top_evening_star
Description: Three-candle reversal pattern: big green → small body → big red
Category: top_escape
"""

FACTOR_NAME = "top_evening_star"
FACTOR_DESC = "Evening star: big green → small body → big red at highs — reversal"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Classic three-candle evening star reversal pattern.
    Day 1: Big green candle (strong buying)
    Day 2: Small body (doji/spinning top) — indecision
    Day 3: Big red candle (sellers take control)
    """
    if idx < 3:
        return 0.5

    # Approximate opens from previous closes
    open1 = closes[idx - 3] if idx >= 3 else closes[idx - 2]
    close1 = closes[idx - 2]
    open2 = close1
    close2 = closes[idx - 1]
    open3 = close2
    close3 = closes[idx]

    range1 = highs[idx - 2] - lows[idx - 2]
    range2 = highs[idx - 1] - lows[idx - 1]
    range3 = highs[idx] - lows[idx]

    if range1 <= 0 or range3 <= 0:
        return 0.5

    # Day 1: Big green candle
    body1 = close1 - open1
    if body1 <= 0:
        return 0.5  # Not green

    body1_ratio = body1 / range1
    if body1_ratio < 0.5:
        return 0.5  # Not a big body

    # Day 2: Small body (doji/spinning top)
    body2 = abs(close2 - open2)
    body2_ratio = body2 / range2 if range2 > 0 else 0

    if body2_ratio > 0.40:
        return 0.5  # Body too large, not a doji/spinning top

    # Day 3: Big red candle
    body3 = open3 - close3
    if body3 <= 0:
        return 0.5  # Not red

    body3_ratio = body3 / range3
    if body3_ratio < 0.5:
        return 0.5  # Not a big body

    # Check that day 3 closes into day 1's body (at least 50%)
    penetration = (close1 - close3) / body1 if body1 > 0 else 0

    if penetration < 0.3:
        return 0.55  # Weak evening star

    # Score based on quality of the pattern
    quality = (body1_ratio + (1.0 - body2_ratio) + body3_ratio) / 3.0
    penetration_score = min(1.0, penetration)

    score = 0.65 + 0.35 * quality * penetration_score

    return max(0.0, min(1.0, score))
