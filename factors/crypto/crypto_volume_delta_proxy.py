"""
Factor: crypto_volume_delta_proxy
Description: Cumulative (up-close volume - down-close volume) over 24 bars
Category: crypto
"""

FACTOR_NAME = "crypto_volume_delta_proxy"
FACTOR_DESC = "Proxy for volume delta using close vs previous close over 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = net buying volume dominance."""
    lookback = 24
    if idx < lookback:
        return 0.5

    up_vol = 0.0
    down_vol = 0.0
    for i in range(idx - lookback + 1, idx + 1):
        if closes[i] > closes[i - 1]:
            up_vol += volumes[i]
        elif closes[i] < closes[i - 1]:
            down_vol += volumes[i]

    total = up_vol + down_vol
    if total <= 0:
        return 0.5

    ratio = up_vol / total  # 0 to 1
    return max(0.0, min(1.0, ratio))
