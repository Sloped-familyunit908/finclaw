"""
Auto-generated factor: descending_triangle
Description: Lower highs with flat lows (bearish triangle, low score)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "descending_triangle"
FACTOR_DESC = "Lower highs with flat lows (bearish triangle, low score)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect descending triangle: lower highs, flat support."""

    lookback = 10
    if idx < lookback:
        return 0.5

    # Collect highs and lows
    low_values = []
    high_values = []
    for i in range(idx - lookback + 1, idx + 1):
        low_values.append(lows[i])
        high_values.append(highs[i])

    # Lower highs: count how many consecutive highs are lower
    lower_highs = 0
    for i in range(1, len(high_values)):
        if high_values[i] <= high_values[i - 1]:
            lower_highs += 1

    # Flat lows: low variation in lows
    max_l = low_values[0]
    min_l = low_values[0]
    sum_l = 0.0
    for l in low_values:
        sum_l += l
        if l > max_l:
            max_l = l
        if l < min_l:
            min_l = l
    avg_l = sum_l / len(low_values)

    flat_support = (max_l - min_l) / avg_l < 0.02 if avg_l > 0 else False

    # Descending triangle: lower highs + flat support = bearish
    lower_high_ratio = lower_highs / float(lookback - 1)

    if lower_high_ratio > 0.6 and flat_support:
        return 0.15  # Strong bearish pattern
    elif lower_high_ratio > 0.6:
        return 0.35
    elif flat_support:
        return 0.45

    return 0.5
