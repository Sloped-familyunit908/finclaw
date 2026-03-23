"""
Factor: crypto_bb_squeeze_duration
Description: How many bars BB width has been contracting
Category: crypto
"""

FACTOR_NAME = "crypto_bb_squeeze_duration"
FACTOR_DESC = "Duration of Bollinger Band squeeze (contracting width)"
FACTOR_CATEGORY = "crypto"


def _bb_width(closes, period, end_idx):
    """Compute BB width at a given index."""
    if end_idx < period:
        return None
    window = closes[end_idx - period + 1:end_idx + 1]
    mean = sum(window) / period
    if mean <= 0:
        return None
    variance = sum((x - mean) ** 2 for x in window) / period
    std = variance ** 0.5
    return (4 * std) / mean


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Higher = longer squeeze (potential breakout coming)."""
    period = 24
    max_lookback = 48
    if idx < period + max_lookback:
        return 0.5

    # Count consecutive bars where BB width is shrinking
    squeeze_count = 0
    for i in range(idx, idx - max_lookback, -1):
        w_now = _bb_width(closes, period, i)
        w_prev = _bb_width(closes, period, i - 1)
        if w_now is None or w_prev is None:
            break
        if w_now < w_prev:
            squeeze_count += 1
        else:
            break

    # Normalize: 0-24 bars of squeeze mapped to 0-1
    score = squeeze_count / 24.0
    return max(0.0, min(1.0, score))
