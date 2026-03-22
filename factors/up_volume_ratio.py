"""
Factor: up_volume_ratio
Description: Ratio of volume on up days vs down days over last 10 days
Category: volume
"""

FACTOR_NAME = "up_volume_ratio"
FACTOR_DESC = "Ratio of volume on up days vs down days over last 10 days"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """More volume on up days = accumulation = bullish."""
    if idx < 11:
        return 0.5

    up_vol = 0.0
    down_vol = 0.0

    for i in range(idx - 9, idx + 1):
        if closes[i] > closes[i - 1]:
            up_vol += volumes[i]
        elif closes[i] < closes[i - 1]:
            down_vol += volumes[i]

    total = up_vol + down_vol
    if total <= 0:
        return 0.5

    ratio = up_vol / total  # 0 to 1, 0.5 = balanced

    # Already in [0, 1] but center around extremes
    # 100% up volume = 1.0, 100% down volume = 0.0
    return max(0.0, min(1.0, ratio))
