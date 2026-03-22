"""
Auto-generated factor: ascending_triangle
Description: Higher lows with flat highs over 10 days (bullish triangle proxy)
Category: pattern
Generated: seed
"""

FACTOR_NAME = "ascending_triangle"
FACTOR_DESC = "Higher lows with flat highs over 10 days (bullish triangle proxy)"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect ascending triangle: higher lows, flat resistance."""

    lookback = 10
    if idx < lookback:
        return 0.5

    # Check for higher lows
    low_values = []
    high_values = []
    for i in range(idx - lookback + 1, idx + 1):
        low_values.append(lows[i])
        high_values.append(highs[i])

    # Higher lows: count how many consecutive lows are higher
    higher_lows = 0
    for i in range(1, len(low_values)):
        if low_values[i] >= low_values[i - 1]:
            higher_lows += 1

    # Flat highs: low standard deviation of highs
    max_h = high_values[0]
    min_h = high_values[0]
    sum_h = 0.0
    for h in high_values:
        sum_h += h
        if h > max_h:
            max_h = h
        if h < min_h:
            min_h = h
    avg_h = sum_h / len(high_values)

    flat_resistance = (max_h - min_h) / avg_h < 0.02 if avg_h > 0 else False

    # Ascending triangle: higher lows + flat resistance
    higher_low_ratio = higher_lows / float(lookback - 1)

    if higher_low_ratio > 0.6 and flat_resistance:
        return 0.85
    elif higher_low_ratio > 0.6:
        return 0.65
    elif flat_resistance:
        return 0.55

    return 0.5
