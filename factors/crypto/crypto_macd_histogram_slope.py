"""
Factor: crypto_macd_histogram_slope
Description: Slope of MACD histogram over 6 bars
Category: crypto
"""

FACTOR_NAME = "crypto_macd_histogram_slope"
FACTOR_DESC = "Slope of MACD histogram over last 6 bars"
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


def _macd_hist(closes, end_idx):
    """Compute MACD histogram at end_idx."""
    ema12 = _ema(closes, 12, end_idx)
    ema26 = _ema(closes, 26, end_idx)
    macd_line = ema12 - ema26
    # Signal line approximated as 9-period EMA of MACD
    # For simplicity, compute MACD for recent bars and average
    macd_vals = []
    start = max(0, end_idx - 9)
    for i in range(start, end_idx + 1):
        e12 = _ema(closes, 12, i)
        e26 = _ema(closes, 26, i)
        macd_vals.append(e12 - e26)
    signal = sum(macd_vals) / len(macd_vals) if macd_vals else 0
    return macd_line - signal


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = histogram rising."""
    if idx < 32:
        return 0.5

    hist_now = _macd_hist(closes, idx)
    hist_prev = _macd_hist(closes, idx - 6)

    if closes[idx] <= 0:
        return 0.5

    slope = (hist_now - hist_prev) / closes[idx]
    score = 0.5 + (slope / 0.005) * 0.4
    return max(0.0, min(1.0, score))
