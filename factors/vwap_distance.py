"""
Auto-generated factor: vwap_distance
Description: Distance from estimated VWAP ((H+L+C)/3)
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "vwap_distance"
FACTOR_DESC = "Distance from estimated VWAP ((H+L+C)/3)"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Distance from estimated VWAP over last 5 days."""

    lookback = 5
    if idx < lookback:
        return 0.5

    # Compute volume-weighted average price
    vwap_num = 0.0
    vwap_den = 0.0

    for i in range(idx - lookback + 1, idx + 1):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3.0
        vwap_num += typical_price * volumes[i]
        vwap_den += volumes[i]

    if vwap_den < 1e-10:
        return 0.5

    vwap = vwap_num / vwap_den

    if vwap < 1e-10:
        return 0.5

    # Distance from VWAP as percentage
    dist = (closes[idx] - vwap) / vwap

    # Above VWAP = bullish (institutions buying above avg), below = bearish
    # Map from [-5%, +5%] to [0, 1]
    score = 0.5 + dist * 10.0
    return max(0.0, min(1.0, score))
