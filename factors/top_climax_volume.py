"""
Factor: top_climax_volume
Description: Extreme volume at price highs signals distribution/top
Category: top_escape
"""

FACTOR_NAME = "top_climax_volume"
FACTOR_DESC = "Extreme volume (>3x avg) near 20-day high — climax top signal"
FACTOR_CATEGORY = "top_escape"


def compute(closes, highs, lows, volumes, idx):
    """Score high when price is near 20-day high AND volume is >3x 20-day average.
    This combination often marks a distribution top where smart money exits
    into retail euphoria.
    """
    period = 20
    if idx < period:
        return 0.5

    # Check if near 20-day high
    high_20d = max(highs[idx - period + 1 : idx + 1])
    if high_20d <= 0:
        return 0.5

    price_nearness = closes[idx] / high_20d  # 1.0 = at the high

    if price_nearness < 0.95:
        # Not near the high — not a top signal
        return 0.5

    # Calculate average volume over 20 days
    vol_sum = 0.0
    vol_count = 0
    for i in range(idx - period + 1, idx + 1):
        if volumes[i] > 0:
            vol_sum += volumes[i]
            vol_count += 1

    if vol_count == 0:
        return 0.5

    avg_vol = vol_sum / vol_count
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio < 2.0:
        return 0.5

    # Score based on how extreme the volume is
    # 2x = 0.6, 3x = 0.8, 4x+ = 1.0
    nearness_score = (price_nearness - 0.95) / 0.05  # 0 to 1
    vol_score = min(1.0, (vol_ratio - 2.0) / 2.0)  # 0 at 2x, 1 at 4x

    score = 0.6 + 0.4 * nearness_score * vol_score

    return max(0.0, min(1.0, score))
