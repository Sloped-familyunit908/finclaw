"""
Auto-generated factor: breakout_probability
Description: Probability of breakout based on consolidation tightness and volume buildup
Category: volatility
Generated: seed
"""

FACTOR_NAME = "breakout_probability"
FACTOR_DESC = "Probability of breakout based on consolidation tightness and volume buildup"
FACTOR_CATEGORY = "volatility"


def compute(closes, highs, lows, volumes, idx):
    """Tightness of last 10 days' range * volume buildup score."""

    if idx < 20:
        return 0.5

    # MA20 for normalization
    ma20 = sum(closes[idx - 19:idx + 1]) / 20.0
    if ma20 <= 0:
        return 0.5

    # Tightness: range of last 10 days relative to MA20
    period_high = highs[idx - 9]
    period_low = lows[idx - 9]
    for i in range(idx - 9, idx + 1):
        if highs[i] > period_high:
            period_high = highs[i]
        if lows[i] < period_low:
            period_low = lows[i]

    range_pct = (period_high - period_low) / ma20

    # Tighter range = higher tightness score
    # range_pct < 0.03 (very tight) → 1.0
    # range_pct > 0.15 (wide) → 0.0
    if range_pct <= 0.03:
        tightness_score = 1.0
    elif range_pct >= 0.15:
        tightness_score = 0.0
    else:
        tightness_score = 1.0 - (range_pct - 0.03) / 0.12

    # Volume buildup: recent 5-day avg volume vs previous 5-day avg volume
    vol_recent = sum(volumes[idx - 4:idx + 1]) / 5.0
    vol_prev = sum(volumes[idx - 9:idx - 4]) / 5.0

    if vol_prev <= 0:
        volume_buildup = 0.5
    else:
        vol_ratio = vol_recent / vol_prev
        # ratio > 1.5 → strong buildup → 1.0
        # ratio < 0.7 → declining → 0.0
        volume_buildup = (vol_ratio - 0.7) / 0.8
        volume_buildup = max(0.0, min(1.0, volume_buildup))

    # Combined score
    score = tightness_score * volume_buildup
    return max(0.0, min(1.0, score))
