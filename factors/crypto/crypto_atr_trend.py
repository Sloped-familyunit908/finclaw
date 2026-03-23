"""
Factor: crypto_atr_trend
Description: ATR (Average True Range) trend — expanding volatility detection
Category: crypto
"""

FACTOR_NAME = "crypto_atr_trend"
FACTOR_DESC = "ATR trend — increasing ATR signals expanding volatility"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = ATR expanding (volatile), Low = ATR contracting (calm)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Compute True Range for each bar
    tr_values = []
    for i in range(idx - lookback + 1, idx + 1):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1]) if i > 0 else tr1
        tr3 = abs(lows[i] - closes[i - 1]) if i > 0 else tr1
        tr_values.append(max(tr1, tr2, tr3))

    if len(tr_values) < lookback:
        return 0.5

    # ATR for first and second halves
    half = len(tr_values) // 2
    atr_first = sum(tr_values[:half]) / half
    atr_second = sum(tr_values[half:]) / len(tr_values[half:])

    if atr_first <= 0:
        return 0.5

    # ATR trend ratio
    atr_ratio = atr_second / atr_first

    # Expanding ATR: >1.0, Contracting: <1.0
    # Map to [0, 1]: ratio 0.5 → 0.0, ratio 1.0 → 0.5, ratio 2.0 → 1.0
    score = min(max(atr_ratio - 0.5, 0) / 1.5, 1.0)

    return max(0.0, min(1.0, score))
