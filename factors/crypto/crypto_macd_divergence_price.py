"""
Factor: crypto_macd_divergence_price
Description: Price making new high but MACD declining (bearish divergence) or vice versa
Category: crypto
"""

FACTOR_NAME = "crypto_macd_divergence_price"
FACTOR_DESC = "MACD-price divergence detection"
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
    """Returns float in [0, 1]. Near 0 = bearish divergence, near 1 = bullish divergence."""
    lookback = 24
    if idx < 26 + lookback:
        return 0.5

    # Compare current vs lookback-ago
    price_now = closes[idx]
    price_ago = closes[idx - lookback]
    macd_now = _ema(closes, 12, idx) - _ema(closes, 26, idx)
    macd_ago = _ema(closes, 12, idx - lookback) - _ema(closes, 26, idx - lookback)

    if price_ago <= 0:
        return 0.5

    price_change = (price_now - price_ago) / price_ago
    macd_change = macd_now - macd_ago

    # Bearish divergence: price up but MACD down
    if price_change > 0.01 and macd_change < 0:
        strength = min(abs(macd_change) / (abs(price_ago) * 0.01 + 1e-10), 1.0)
        return max(0.0, 0.5 - strength * 0.4)

    # Bullish divergence: price down but MACD up
    if price_change < -0.01 and macd_change > 0:
        strength = min(abs(macd_change) / (abs(price_ago) * 0.01 + 1e-10), 1.0)
        return min(1.0, 0.5 + strength * 0.4)

    return 0.5
