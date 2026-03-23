"""
Factor: crypto_ma_convergence
Description: Distance between EMA(12) and EMA(24) shrinking or expanding
Category: crypto
"""

FACTOR_NAME = "crypto_ma_convergence"
FACTOR_DESC = "EMA(12)/EMA(24) convergence or divergence"
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
    """Returns float in [0, 1]. Above 0.5 = MAs converging (squeeze), below = diverging."""
    if idx < 25:
        return 0.5

    ema12_now = _ema(closes, 12, idx)
    ema24_now = _ema(closes, 24, idx)
    ema12_prev = _ema(closes, 12, idx - 1)
    ema24_prev = _ema(closes, 24, idx - 1)

    if ema24_now <= 0 or ema24_prev <= 0:
        return 0.5

    gap_now = abs(ema12_now - ema24_now) / ema24_now
    gap_prev = abs(ema12_prev - ema24_prev) / ema24_prev

    # Converging = gap shrinking = positive signal
    delta = gap_prev - gap_now

    score = 0.5 + (delta / 0.005) * 0.3
    return max(0.0, min(1.0, score))
