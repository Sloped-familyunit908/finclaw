"""
Factor: trend_breakout_new_high
Description: New 20-day high on above-average volume — breakout confirmation
Category: trend_following
"""

FACTOR_NAME = "trend_breakout_new_high"
FACTOR_DESC = "New 20-day high with above-average volume — breakout confirmation"
FACTOR_CATEGORY = "trend_following"


def compute(closes, highs, lows, volumes, idx):
    """Price making new 20-day high with above-average volume.
    Volume confirms the breakout is backed by conviction.
    """
    period = 20
    if idx < period:
        return 0.5

    # Check if today's high is a new 20-day high
    prev_high = max(highs[idx - period : idx])  # Previous 20 days (not including today)
    is_new_high = highs[idx] > prev_high

    if not is_new_high:
        return 0.5

    # Calculate volume ratio
    vol_sum = sum(volumes[idx - period + 1 : idx + 1])
    avg_vol = vol_sum / period
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio < 0.8:
        # New high but on low volume — suspicious breakout
        return 0.55

    # How much above the previous high?
    if prev_high > 0:
        breakout_margin = (highs[idx] - prev_high) / prev_high
    else:
        breakout_margin = 0

    # Score: new high confirmed by volume
    margin_score = min(1.0, breakout_margin / 0.03)  # 3% above prior high = max
    vol_score = min(1.0, (vol_ratio - 0.8) / 1.2)  # 0.8x→0, 2x→1

    score = 0.65 + 0.35 * (0.5 * margin_score + 0.5 * vol_score)

    return max(0.0, min(1.0, score))
