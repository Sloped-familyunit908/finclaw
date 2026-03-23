"""
Factor: crypto_accumulation_48h
Description: Gradually increasing volume floor with stable price — accumulation
Category: crypto
"""

FACTOR_NAME = "crypto_accumulation_48h"
FACTOR_DESC = "Increasing volume floor with stable price over 48h — accumulation pattern"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = accumulation detected (bullish)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Split into two 24h halves
    first_half_vols = volumes[idx - lookback:idx - 24]
    second_half_vols = volumes[idx - 24:idx]

    if not first_half_vols or not second_half_vols:
        return 0.5

    # Volume floor = minimum volume in each half
    floor_1 = min(first_half_vols)
    floor_2 = min(second_half_vols)

    avg_1 = sum(first_half_vols) / len(first_half_vols)
    avg_2 = sum(second_half_vols) / len(second_half_vols)

    # Check if volume floor is rising
    if floor_1 <= 0:
        return 0.5
    floor_increase = (floor_2 - floor_1) / floor_1

    # Check if price is stable (< 2% change over 48h)
    if closes[idx - lookback] <= 0:
        return 0.5
    price_change = abs(closes[idx] - closes[idx - lookback]) / closes[idx - lookback]

    if price_change > 0.02:
        # Price not stable enough for accumulation
        return 0.5

    if floor_increase <= 0:
        return 0.5

    # Also check average volume increase
    avg_increase = (avg_2 - avg_1) / avg_1 if avg_1 > 0 else 0

    # Combine floor increase and average increase
    combined = (floor_increase + max(avg_increase, 0)) / 2.0
    score = 0.5 + min(combined / 0.5, 1.0) * 0.4

    return max(0.0, min(1.0, score))
