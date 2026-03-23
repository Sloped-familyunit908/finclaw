"""
Factor: crypto_adaptive_ema
Description: EMA with period adjusted by volatility (fast in high vol)
Category: crypto
"""

FACTOR_NAME = "crypto_adaptive_ema"
FACTOR_DESC = "EMA with period adjusted by volatility (fast in high vol)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = price above adaptive EMA."""
    base_period = 24
    if idx < base_period + 1:
        return 0.5

    # Volatility-adjusted period
    returns = []
    for i in range(idx - base_period, idx):
        if i < 1 or closes[i - 1] <= 0:
            continue
        returns.append(abs((closes[i] - closes[i - 1]) / closes[i - 1]))

    avg_vol = sum(returns) / len(returns) if returns else 0.01
    # Higher vol -> shorter period (faster adaptation)
    adjusted_period = max(5, min(48, int(base_period * 0.01 / max(avg_vol, 0.001))))

    mult = 2.0 / (adjusted_period + 1)
    ema = closes[max(0, idx - adjusted_period - 1)]
    start = max(1, idx - adjusted_period)
    for i in range(start, idx):
        ema = closes[i] * mult + ema * (1 - mult)

    if ema <= 0:
        return 0.5

    diff = (closes[idx - 1] - ema) / ema
    score = 0.5 + diff * 15.0
    return max(0.0, min(1.0, score))
