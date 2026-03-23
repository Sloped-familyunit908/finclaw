"""
Factor: crypto_macd_zero_cross
Description: How recently MACD line crossed zero
Category: crypto
"""

FACTOR_NAME = "crypto_macd_zero_cross"
FACTOR_DESC = "Recency of MACD line zero crossing"
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
    """Returns float in [0, 1]. Near 1.0 = just crossed above zero, near 0.0 = just crossed below."""
    if idx < 27:
        return 0.5

    lookback = 24
    for bars_ago in range(1, lookback + 1):
        i = idx - bars_ago
        if i < 26:
            break
        macd_now = _ema(closes, 12, i + 1) - _ema(closes, 26, i + 1)
        macd_prev = _ema(closes, 12, i) - _ema(closes, 26, i)

        if macd_prev <= 0 and macd_now > 0:
            # Bullish cross, more recent = higher score
            recency = 1.0 - (bars_ago / lookback)
            return max(0.0, min(1.0, 0.5 + recency * 0.5))
        elif macd_prev >= 0 and macd_now < 0:
            # Bearish cross
            recency = 1.0 - (bars_ago / lookback)
            return max(0.0, min(1.0, 0.5 - recency * 0.5))

    return 0.5
