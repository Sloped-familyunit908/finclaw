"""
Auto-generated factor: institutional_buying_proxy
Description: Steady price increase on increasing volume over 20 days
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "institutional_buying_proxy"
FACTOR_DESC = "Steady price increase on increasing volume over 20 days"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect steady price increase with increasing volume over 20 days."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Count up days and check if volume is trending up
    up_days = 0
    vol_increases = 0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_days += 1
        if volumes[i] > volumes[i - 1]:
            vol_increases += 1

    up_ratio = up_days / float(lookback)
    vol_increase_ratio = vol_increases / float(lookback)

    # Overall price trend
    price_return = (closes[idx] - closes[idx - lookback]) / closes[idx - lookback] if closes[idx - lookback] > 0 else 0.0

    # Institutional buying: steady up + increasing volume + positive return
    if price_return > 0 and up_ratio > 0.55 and vol_increase_ratio > 0.45:
        score = 0.5 + up_ratio * 0.3 + price_return * 2.0
        return max(0.0, min(1.0, score))

    return 0.5 + price_return * 0.5
