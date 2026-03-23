"""
Factor: crypto_price_vs_ema_24
Description: Distance from 24-bar EMA as % of price
Category: crypto
"""

FACTOR_NAME = "crypto_price_vs_ema_24"
FACTOR_DESC = "Price distance from 24-bar EMA"
FACTOR_CATEGORY = "crypto"


def _ema(data, period, end_idx):
    """Compute EMA ending at end_idx."""
    if end_idx < period:
        return sum(data[:end_idx + 1]) / (end_idx + 1) if end_idx >= 0 else 0
    k = 2.0 / (period + 1)
    start = end_idx - period * 3
    if start < 0:
        start = 0
    val = sum(data[start:start + period]) / period
    for i in range(start + period, end_idx + 1):
        val = data[i] * k + val * (1 - k)
    return val


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = price above EMA24."""
    if idx < 24:
        return 0.5

    ema24 = _ema(closes, 24, idx)
    if ema24 <= 0:
        return 0.5

    dist_pct = (closes[idx] - ema24) / ema24

    # Normalize: typical range -5% to +5%
    score = 0.5 + (dist_pct / 0.10)
    return max(0.0, min(1.0, score))
