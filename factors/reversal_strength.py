"""
Auto-generated factor: reversal_strength
Description: Size of bounce from recent low + volume confirmation
Category: composite
Generated: seed
"""

FACTOR_NAME = "reversal_strength"
FACTOR_DESC = "Size of bounce from recent low + volume confirmation"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Reversal strength: bounce size from recent low with volume."""

    lookback = 15
    if idx < lookback:
        return 0.5

    # Find recent low
    min_low = lows[idx]
    min_idx = idx
    for i in range(idx - lookback, idx):
        if lows[i] < min_low:
            min_low = lows[i]
            min_idx = i

    if min_low < 1e-10:
        return 0.5

    # Bounce size
    bounce_pct = (closes[idx] - min_low) / min_low

    # Volume on bounce vs volume at low
    vol_at_low = volumes[min_idx]
    vol_now = volumes[idx]
    vol_confirmation = vol_now > vol_at_low if vol_at_low > 0 else False

    # Days since low
    days_since_low = idx - min_idx

    score = 0.5
    if bounce_pct > 0.02 and days_since_low > 0 and days_since_low < 10:
        score += bounce_pct * 3.0
        if vol_confirmation:
            score += 0.1

    return max(0.0, min(1.0, score))
