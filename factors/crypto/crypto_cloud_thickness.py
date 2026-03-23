"""
Factor: crypto_cloud_thickness
Description: Senkou A - Senkou B (cloud width) normalized
Category: crypto
"""

FACTOR_NAME = "crypto_cloud_thickness"
FACTOR_DESC = "Senkou A - Senkou B (cloud width) normalized"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = bullish cloud (A>B), <0.5 = bearish cloud."""
    if idx < 52:
        return 0.5

    tenkan = (max(highs[idx - 9:idx]) + min(lows[idx - 9:idx])) / 2.0
    kijun = (max(highs[idx - 26:idx]) + min(lows[idx - 26:idx])) / 2.0
    senkou_a = (tenkan + kijun) / 2.0
    senkou_b = (max(highs[idx - 52:idx]) + min(lows[idx - 52:idx])) / 2.0

    if closes[idx - 1] <= 0:
        return 0.5

    diff = (senkou_a - senkou_b) / closes[idx - 1]
    score = 0.5 + diff * 20.0
    return max(0.0, min(1.0, score))
