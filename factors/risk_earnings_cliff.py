"""
Factor: risk_earnings_cliff
Description: Sudden >5% gap down on >3x volume — likely bad news
Category: risk_warning
"""

FACTOR_NAME = "risk_earnings_cliff"
FACTOR_DESC = "Gap down >5% on >3x volume — likely bad earnings or news shock"
FACTOR_CATEGORY = "risk_warning"


def compute(closes, highs, lows, volumes, idx):
    """Sudden >5% gap down on >3x volume.
    Likely bad earnings or major news event.
    """
    if idx < 20:
        return 0.5

    prev_close = closes[idx - 1]
    if prev_close <= 0:
        return 0.5

    # Gap down size (using low as proxy for open)
    gap_pct = (prev_close - lows[idx]) / prev_close

    # Also check close-to-close drop
    drop_pct = (prev_close - closes[idx]) / prev_close

    if drop_pct < 0.03:
        return 0.5  # Less than 3% drop — not significant

    # Calculate average volume
    vol_sum = sum(volumes[idx - 20 : idx])  # 20 days before today
    avg_vol = vol_sum / 20
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    if vol_ratio < 1.5:
        return 0.5  # Not high volume — probably not earnings

    # Score based on drop size AND volume confirmation
    drop_score = min(1.0, drop_pct / 0.10)  # 10% drop = max
    vol_score = min(1.0, (vol_ratio - 1.5) / 3.5)  # 1.5x→0, 5x→1

    # Both need to be present
    if drop_pct >= 0.05 and vol_ratio >= 3.0:
        base = 0.85
    elif drop_pct >= 0.05 or vol_ratio >= 3.0:
        base = 0.7
    else:
        base = 0.6

    score = base + 0.15 * (drop_score + vol_score) / 2.0

    return max(0.0, min(1.0, score))
