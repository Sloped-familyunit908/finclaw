"""
Factor: crypto_atr_ratio
Description: ATR(12)/ATR(48) - expanding or contracting volatility
Category: crypto
"""

FACTOR_NAME = "crypto_atr_ratio"
FACTOR_DESC = "ATR(12)/ATR(48) ratio - volatility expansion/contraction"
FACTOR_CATEGORY = "crypto"


def _atr(closes, highs, lows, period, end_idx):
    """Compute ATR at end_idx."""
    if end_idx < period + 1:
        return None
    atr_sum = 0.0
    for i in range(end_idx - period + 1, end_idx + 1):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        atr_sum += max(tr1, tr2, tr3)
    return atr_sum / period


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Above 0.5 = short-term vol expanding vs long-term."""
    if idx < 49:
        return 0.5

    atr12 = _atr(closes, highs, lows, 12, idx)
    atr48 = _atr(closes, highs, lows, 48, idx)

    if atr12 is None or atr48 is None or atr48 <= 0:
        return 0.5

    ratio = atr12 / atr48

    # ratio=1.0 is neutral, >1 means expanding, <1 means contracting
    score = 0.5 + (ratio - 1.0) * 0.5
    return max(0.0, min(1.0, score))
