"""
Auto-generated factor: insider_proxy
Description: Unusual volume spike before price move (possible insider activity)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "insider_proxy"
FACTOR_DESC = "Unusual volume spike before price move (possible insider activity)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect unusual volume spike preceding a price move."""

    lookback = 20
    if idx < lookback + 3:
        return 0.5

    # Average and std of volume over lookback
    vol_total = 0.0
    for i in range(idx - lookback - 3, idx - 3):
        vol_total += volumes[i]
    avg_vol = vol_total / lookback

    vol_var = 0.0
    for i in range(idx - lookback - 3, idx - 3):
        diff = volumes[i] - avg_vol
        vol_var += diff * diff
    vol_std = (vol_var / lookback) ** 0.5

    if vol_std < 1e-10:
        return 0.5

    # Check for volume spike 1-3 days ago
    max_vol_spike = 0.0
    for i in range(idx - 3, idx):
        vol_z = (volumes[i] - avg_vol) / vol_std
        if vol_z > max_vol_spike:
            max_vol_spike = vol_z

    # Check if price has moved since the spike
    price_change = (closes[idx] - closes[idx - 3]) / closes[idx - 3] if closes[idx - 3] > 0 else 0.0

    # Insider proxy: high volume spike followed by price move
    if max_vol_spike > 2.0:
        if price_change > 0.01:
            # Bullish insider activity
            score = 0.5 + max_vol_spike * 0.05 + price_change * 3.0
            return max(0.0, min(1.0, score))
        elif price_change < -0.01:
            # Bearish insider activity
            score = 0.5 - max_vol_spike * 0.05 - abs(price_change) * 3.0
            return max(0.0, min(1.0, score))

    return 0.5
