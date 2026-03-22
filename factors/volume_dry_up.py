"""
Factor: volume_dry_up
Description: Volume < 50% of 20-day average (drying up, often precedes move)
Category: volume
"""

FACTOR_NAME = "volume_dry_up"
FACTOR_DESC = "Volume < 50% of 20-day average (drying up, often precedes move)"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Low volume = energy building up, potential breakout ahead."""
    if idx < 20:
        return 0.5

    avg_vol = sum(volumes[idx - 19:idx + 1]) / 20
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio < 0.3:
        # Very dry = strong signal
        score = 0.85
    elif vol_ratio < 0.5:
        # Dry
        score = 0.7
    elif vol_ratio < 0.7:
        # Below average but not extremely dry
        score = 0.55
    else:
        # Normal or above average volume
        score = 0.5

    return max(0.0, min(1.0, score))
