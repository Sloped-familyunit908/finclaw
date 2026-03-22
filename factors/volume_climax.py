"""
Factor: volume_climax
Description: Volume > 3x 20-day average (climax volume)
Category: volume
"""

FACTOR_NAME = "volume_climax"
FACTOR_DESC = "Volume > 3x 20-day average (climax volume, often marks top or bottom)"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Extreme volume often marks reversals. Bullish if at bottom."""
    if idx < 20:
        return 0.5

    avg_vol = sum(volumes[idx - 19:idx + 1]) / 20
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio < 2.0:
        return 0.5

    # Climax volume detected. Context matters:
    # At relative low = bullish capitulation, at high = bearish distribution
    recent_high = max(closes[idx - 19:idx + 1])
    recent_low = min(closes[idx - 19:idx + 1])
    price_range = recent_high - recent_low

    if price_range <= 0:
        return 0.5

    position = (closes[idx] - recent_low) / price_range

    if position < 0.3:
        # Climax at bottom = capitulation = bullish
        score = 0.7 + min((vol_ratio - 2.0) * 0.1, 0.25)
    elif position > 0.7:
        # Climax at top = distribution = bearish
        score = 0.3 - min((vol_ratio - 2.0) * 0.1, 0.2)
    else:
        # Middle = neutral
        score = 0.5

    return max(0.0, min(1.0, score))
