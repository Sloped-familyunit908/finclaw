"""
Auto-generated factor: earnings_surprise_proxy
Description: Sudden gap up on high volume (proxy for positive earnings surprise)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "earnings_surprise_proxy"
FACTOR_DESC = "Sudden gap up on high volume (proxy for positive earnings surprise)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect gap up on high volume as earnings surprise proxy."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Gap: today's open proxy (low) vs yesterday's close
    gap_pct = (lows[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] > 0 else 0.0

    # Volume ratio
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback
    vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0

    # Positive surprise: gap up > 2% AND volume > 2x average
    if gap_pct > 0.02 and vol_ratio > 2.0:
        strength = gap_pct * 5.0 + (vol_ratio - 2.0) * 0.1
        score = 0.5 + strength
        return max(0.0, min(1.0, score))

    # Negative surprise: gap down on high volume
    if gap_pct < -0.02 and vol_ratio > 2.0:
        strength = abs(gap_pct) * 5.0
        score = 0.5 - strength
        return max(0.0, min(1.0, score))

    return 0.5
