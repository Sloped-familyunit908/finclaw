"""
Factor: crypto_volume_spike
Description: Volume spike relative to 24h average (24-bar lookback for 1h data)
Category: crypto
"""

FACTOR_NAME = "crypto_volume_spike"
FACTOR_DESC = "Volume spike relative to 24-hour rolling average — detects sudden liquidity surges in crypto"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Measures current volume relative to the 24-bar average.
    High volume spikes often signal institutional activity or breakout.
    Returns 0.5 at average volume, >0.5 for above-average, <0.5 for below.
    """
    lookback = 24
    if idx < lookback:
        return 0.5

    avg_vol = sum(volumes[idx - lookback:idx]) / lookback
    if avg_vol <= 0:
        return 0.5

    current_vol = volumes[idx]
    ratio = current_vol / avg_vol

    # ratio=1 -> 0.5, ratio=3+ -> 1.0, ratio=0 -> 0.0
    score = ratio / 6.0  # 0x->0, 3x->0.5, 6x->1.0
    # Shift so 1x average is ~0.3 and spikes stand out
    score = 0.3 + (ratio - 1.0) * 0.14
    score = max(0.0, min(1.0, score))
    return score
