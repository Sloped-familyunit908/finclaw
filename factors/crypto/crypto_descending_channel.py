"""
Factor: crypto_descending_channel
Description: Lower highs AND lower lows over 48 bars — bearish channel
Category: crypto
"""

FACTOR_NAME = "crypto_descending_channel"
FACTOR_DESC = "Descending price channel — lower highs and lower lows over 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = strong descending channel (bearish)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Split into 4 segments of 12 bars each
    seg_size = lookback // 4
    seg_highs = []
    seg_lows = []
    for s in range(4):
        start = idx - lookback + s * seg_size
        end = start + seg_size
        seg_highs.append(max(highs[start:end]))
        seg_lows.append(min(lows[start:end]))

    # Count lower highs and lower lows
    lh_count = 0
    ll_count = 0
    for i in range(1, 4):
        if seg_highs[i] < seg_highs[i - 1]:
            lh_count += 1
        if seg_lows[i] < seg_lows[i - 1]:
            ll_count += 1

    # Both should be consistently falling for a descending channel
    total = (lh_count + ll_count) / 6.0
    score = 0.5 - total * 0.5  # Descending → lower score
    return max(0.0, min(1.0, score))
