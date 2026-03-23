"""
Factor: crypto_macd_acceleration
Description: Second derivative of MACD histogram
Category: crypto
"""

FACTOR_NAME = "crypto_macd_acceleration"
FACTOR_DESC = "Second derivative of MACD histogram (acceleration)"
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


def _macd_line(closes, end_idx):
    return _ema(closes, 12, end_idx) - _ema(closes, 26, end_idx)


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = MACD accelerating upward."""
    if idx < 28:
        return 0.5

    m0 = _macd_line(closes, idx)
    m1 = _macd_line(closes, idx - 1)
    m2 = _macd_line(closes, idx - 2)

    # First derivative
    d1_now = m0 - m1
    d1_prev = m1 - m2
    # Second derivative
    accel = d1_now - d1_prev

    if closes[idx] <= 0:
        return 0.5

    normalized = accel / (closes[idx] * 0.001 + 1e-10)
    score = 0.5 + normalized * 5.0
    return max(0.0, min(1.0, score))
