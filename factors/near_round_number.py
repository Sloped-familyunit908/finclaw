"""
Factor: near_round_number
Description: Price near round number (10, 20, 50, 100) — psychological levels
Category: support_resistance
"""

FACTOR_NAME = "near_round_number"
FACTOR_DESC = "Price near round psychological number levels (10, 50, 100, etc.)"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Check if price is near a round number. These act as S/R levels."""
    if idx < 1:
        return 0.5

    price = closes[idx]
    if price <= 0:
        return 0.5

    # Find the most relevant round number based on price magnitude
    # For price 15: round numbers are 10, 20
    # For price 150: round numbers are 100, 200
    # For price 1500: round numbers are 1000, 2000

    # Determine the scale
    if price >= 1000:
        levels = [100, 500, 1000]
    elif price >= 100:
        levels = [10, 50, 100]
    elif price >= 10:
        levels = [5, 10, 50]
    else:
        levels = [1, 5, 10]

    min_distance_pct = 1.0  # Start with 100%
    for level in levels:
        if level <= 0:
            continue
        # Distance to nearest multiple of this level
        nearest = round(price / level) * level
        distance = abs(price - nearest)
        distance_pct = distance / price
        if distance_pct < min_distance_pct:
            min_distance_pct = distance_pct

    # Very close to round number = interesting level
    # Within 1% = near round number, >5% = not near
    if min_distance_pct < 0.005:
        # Right at it — could break either way
        approaching_from_below = closes[idx] > closes[idx - 1]
        score = 0.65 if approaching_from_below else 0.45
    elif min_distance_pct < 0.02:
        score = 0.6
    elif min_distance_pct < 0.05:
        score = 0.55
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
