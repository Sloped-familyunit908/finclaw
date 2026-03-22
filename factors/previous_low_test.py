"""
Factor: previous_low_test
Description: Price testing/approaching previous 20-day low (support)
Category: support_resistance
"""

FACTOR_NAME = "previous_low_test"
FACTOR_DESC = "Price testing previous 20-day low — support bounce potential"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """How close is price to the 20-day low (support test)."""
    lookback = 20
    if idx < lookback:
        return 0.5

    # Previous low (excluding today)
    prev_low = min(lows[idx - lookback + 1:idx])
    if prev_low <= 0:
        return 0.5

    price = closes[idx]

    if price < prev_low:
        # Breakdown below support
        breakdown_pct = (prev_low - price) / prev_low
        score = 0.2 - min(breakdown_pct * 10, 0.15)
    else:
        distance_pct = (price - prev_low) / prev_low if prev_low > 0 else 0

        if distance_pct < 0.01:
            # At support — bounce potential (bullish)
            score = 0.7
        elif distance_pct < 0.03:
            score = 0.65
        elif distance_pct < 0.05:
            score = 0.6
        elif distance_pct < 0.10:
            score = 0.55
        else:
            score = 0.5

    return max(0.0, min(1.0, score))
