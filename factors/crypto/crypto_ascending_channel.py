"""
Factor: crypto_ascending_channel
Description: Higher highs AND higher lows over 48 bars — bullish channel
Category: crypto
"""

FACTOR_NAME = "crypto_ascending_channel"
FACTOR_DESC = "Ascending price channel — higher highs and higher lows over 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = strong ascending channel."""
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

    # Count higher highs and higher lows
    hh_count = 0
    hl_count = 0
    for i in range(1, 4):
        if seg_highs[i] > seg_highs[i - 1]:
            hh_count += 1
        if seg_lows[i] > seg_lows[i - 1]:
            hl_count += 1

    # Both should be consistently rising for a channel
    total = (hh_count + hl_count) / 6.0  # max 6 (3+3)
    score = 0.5 + total * 0.5
    return max(0.0, min(1.0, score))
