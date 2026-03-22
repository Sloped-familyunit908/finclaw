"""
Factor: resistance_breakout
Description: Price breaking above recent resistance (highest high of last 20 days)
Category: support_resistance
"""

FACTOR_NAME = "resistance_breakout"
FACTOR_DESC = "Price breaking above 20-day resistance — breakout confirmation"
FACTOR_CATEGORY = "support_resistance"


def compute(closes, highs, lows, volumes, idx):
    """Detect price breaking above the highest high of the last 20 days."""
    lookback = 20
    if idx < lookback:
        return 0.5

    # Resistance = highest high in prior days (excluding today)
    resistance = max(highs[idx - lookback:idx])
    price = closes[idx]

    if resistance <= 0:
        return 0.5

    if price > resistance:
        # Clean breakout
        breakout_pct = (price - resistance) / resistance

        # Stronger if with volume
        if idx >= lookback:
            avg_vol = sum(volumes[idx - lookback:idx]) / lookback
            vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0
        else:
            vol_ratio = 1.0

        base_score = 0.75 + min(breakout_pct * 10, 0.1)
        volume_bonus = min((vol_ratio - 1.0) * 0.05, 0.1) if vol_ratio > 1.0 else 0.0
        score = base_score + volume_bonus

    elif price > resistance * 0.98:
        # Testing resistance
        score = 0.6
    else:
        # Below resistance
        distance = (resistance - price) / resistance
        score = 0.5 - min(distance * 5, 0.2)

    return max(0.0, min(1.0, score))
