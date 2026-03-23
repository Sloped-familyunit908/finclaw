"""
Factor: crypto_trend_score
Description: Composite: EMA alignment + ADX proxy + momentum direction
Category: crypto
"""

FACTOR_NAME = "crypto_trend_score"
FACTOR_DESC = "Composite trend score: EMA + ADX proxy + momentum"
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
    """Returns float in [0, 1]. Above 0.5 = strong uptrend, below = strong downtrend."""
    if idx < 48:
        return 0.5

    # Component 1: EMA alignment (EMA12 vs EMA24 vs EMA48)
    ema12 = _ema(closes, 12, idx)
    ema24 = _ema(closes, 24, idx)
    ema48 = _ema(closes, 48, idx)

    alignment = 0.0
    if ema12 > ema24:
        alignment += 0.33
    if ema24 > ema48:
        alignment += 0.33
    if ema12 > ema48:
        alignment += 0.34

    # Component 2: ADX proxy (directional movement strength)
    up_moves = 0
    down_moves = 0
    for i in range(idx - 14, idx):
        if closes[i + 1] > closes[i]:
            up_moves += 1
        elif closes[i + 1] < closes[i]:
            down_moves += 1
    direction = abs(up_moves - down_moves) / 14.0  # 0 = choppy, 1 = directional

    # Component 3: momentum direction
    if closes[idx - 12] > 0:
        momentum = (closes[idx] - closes[idx - 12]) / closes[idx - 12]
    else:
        momentum = 0

    mom_score = 0.5 + (momentum / 0.10)
    mom_score = max(0.0, min(1.0, mom_score))

    # Weighted composite
    score = alignment * 0.4 + direction * 0.2 + mom_score * 0.4
    return max(0.0, min(1.0, score))
