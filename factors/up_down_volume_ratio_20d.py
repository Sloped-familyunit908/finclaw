"""
Auto-generated factor: up_down_volume_ratio_20d
Description: Total volume on up days / total volume on down days (20d window)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "up_down_volume_ratio_20d"
FACTOR_DESC = "Total volume on up days / total volume on down days (20d window)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Ratio of up-day volume to down-day volume over 20 days."""

    lookback = 20
    if idx < lookback:
        return 0.5

    up_volume = 0.0
    down_volume = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_volume += volumes[i]
        elif closes[i] < closes[i - 1]:
            down_volume += volumes[i]

    if down_volume < 1e-10:
        return 0.85 if up_volume > 0 else 0.5

    ratio = up_volume / down_volume

    # Ratio > 1 = more volume on up days = bullish
    # Map ratio from [0, 3] to [0, 1]
    score = ratio / 3.0
    return max(0.0, min(1.0, score))
