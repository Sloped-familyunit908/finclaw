"""
Auto-generated factor: accumulation_distribution_ratio
Description: Ratio of accumulation vs distribution days over 20 days
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "accumulation_distribution_ratio"
FACTOR_DESC = "Ratio of accumulation vs distribution days over 20 days"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Count accumulation vs distribution days over 20 days."""

    lookback = 20
    if idx < lookback + 1:
        return 0.5

    # Average volume
    vol_total = 0.0
    for i in range(idx - lookback, idx):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback

    acc_days = 0
    dist_days = 0

    for i in range(idx - lookback + 1, idx + 1):
        daily_return = (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] > 0 else 0.0
        above_avg = volumes[i] > avg_vol

        if daily_return > 0.002 and above_avg:
            acc_days += 1
        elif daily_return < -0.002 and above_avg:
            dist_days += 1

    total = acc_days + dist_days
    if total == 0:
        return 0.5

    ratio = acc_days / float(total)
    return max(0.0, min(1.0, ratio))
