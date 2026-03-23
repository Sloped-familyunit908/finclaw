"""
Factor: crypto_overextension
Description: Distance from 72h VWAP + 24h extremes — overextension detection
Category: crypto
"""

FACTOR_NAME = "crypto_overextension"
FACTOR_DESC = "Overextension from 72h VWAP and 24h extremes — mean reversion signal"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Near 0.5 = fair value, extremes = overextended."""
    lookback_vwap = 72
    lookback_extremes = 24
    if idx < lookback_vwap:
        return 0.5

    # Compute 72h VWAP
    total_pv = 0.0
    total_v = 0.0
    for i in range(idx - lookback_vwap + 1, idx + 1):
        typical_price = (highs[i] + lows[i] + closes[i]) / 3.0
        total_pv += typical_price * volumes[i]
        total_v += volumes[i]

    if total_v <= 0:
        return 0.5

    vwap = total_pv / total_v

    if vwap <= 0:
        return 0.5

    # Distance from VWAP
    vwap_deviation = (closes[idx] - vwap) / vwap

    # 24h extremes
    high_24h = max(highs[idx - lookback_extremes:idx + 1])
    low_24h = min(lows[idx - lookback_extremes:idx + 1])
    range_24h = high_24h - low_24h

    if range_24h <= 0:
        return 0.5

    # Position relative to 24h range
    range_position = (closes[idx] - low_24h) / range_24h

    # Combine VWAP deviation and range position
    # VWAP deviation: far above = overextended bullish → closer to 1.0
    # Range position: near high = closer to 1.0
    vwap_score = 0.5 + vwap_deviation / 0.06 * 0.5  # ±3% maps to [0, 1]
    vwap_score = max(0.0, min(1.0, vwap_score))

    combined = vwap_score * 0.6 + range_position * 0.4

    return max(0.0, min(1.0, combined))
