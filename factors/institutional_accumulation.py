"""
Auto-generated factor: institutional_accumulation
Description: Detects institutional buying: price up on high volume, price down on low volume pattern
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "institutional_accumulation"
FACTOR_DESC = "Detects institutional buying: price up on high volume, price down on low volume pattern"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Over last 20 days, ratio of up-volume days vs down-volume days, normalized to [0,1]."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Average volume over the window
    vol_sum = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        vol_sum += volumes[i]
    avg_vol = vol_sum / float(lookback)

    if avg_vol <= 0:
        return 0.5

    up_volume_days = 0
    down_volume_days = 0

    for i in range(idx - lookback + 1, idx + 1):
        if i < 1:
            continue
        price_change = closes[i] - closes[i - 1]
        high_volume = volumes[i] > avg_vol

        if price_change > 0 and high_volume:
            up_volume_days += 1
        elif price_change < 0 and high_volume:
            down_volume_days += 1

    total = up_volume_days + down_volume_days
    if total == 0:
        return 0.5

    # Ratio of up-volume days to total high-volume days
    score = up_volume_days / float(total)
    return max(0.0, min(1.0, score))
