"""
Factor: risk_volume_crash
Description: Volume drops to <30% of 20-day average — liquidity desert
Category: risk_warning
"""

FACTOR_NAME = "risk_volume_crash"
FACTOR_DESC = "Volume <30% of 20-day average — liquidity desert, hard to exit"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Volume drops to <30% of 20-day average.
    Liquidity desert = hard to exit position. Dangerous.
    """
    period = 20
    if idx < period:
        return 0.5

    # Calculate 20-day average volume
    vol_sum = sum(volumes[idx - period + 1 : idx + 1])
    avg_vol = vol_sum / period

    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio >= 0.5:
        return 0.5  # Volume is normal

    if vol_ratio >= 0.30:
        # Somewhat low — mild warning
        score = 0.5 + (0.5 - vol_ratio) / 0.2 * 0.2
        return max(0.0, min(1.0, score))

    # Below 30% — serious liquidity concern
    # Lower volume = higher risk score
    if vol_ratio <= 0.05:
        return 1.0  # Almost no trading — extremely dangerous

    score = 0.7 + (0.30 - vol_ratio) / 0.25 * 0.3

    return max(0.0, min(1.0, score))
