"""
Factor: crypto_macd_width
Description: Distance between MACD and signal lines
Category: crypto
"""

FACTOR_NAME = "crypto_macd_width"
FACTOR_DESC = "Distance between MACD line and signal line"
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
    """Returns float in [0, 1]. Above 0.5 = MACD above signal (bullish)."""
    if idx < 35:
        return 0.5

    # Compute MACD values for signal line
    macd_vals = []
    for i in range(idx - 8, idx + 1):
        e12 = _ema(closes, 12, i)
        e26 = _ema(closes, 26, i)
        macd_vals.append(e12 - e26)

    macd_line = macd_vals[-1]
    signal_line = sum(macd_vals) / len(macd_vals)

    diff = macd_line - signal_line

    if closes[idx] <= 0:
        return 0.5

    normalized = diff / (closes[idx] * 0.005 + 1e-10)
    score = 0.5 + normalized * 0.3
    return max(0.0, min(1.0, score))
