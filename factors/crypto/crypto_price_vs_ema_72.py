"""
Factor: crypto_price_vs_ema_72
Description: Distance from 72-bar EMA as % of price
Category: crypto
"""

FACTOR_NAME = "crypto_price_vs_ema_72"
FACTOR_DESC = "Price distance from 72-bar EMA"
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
    """Returns float in [0, 1]. Above 0.5 = price above EMA72."""
    if idx < 72:
        return 0.5

    ema72 = _ema(closes, 72, idx)
    if ema72 <= 0:
        return 0.5

    dist_pct = (closes[idx] - ema72) / ema72

    # Normalize: typical range -10% to +10%
    score = 0.5 + (dist_pct / 0.20)
    return max(0.0, min(1.0, score))
