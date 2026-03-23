"""
Factor: crypto_session_transition
Description: Volatility change at session boundaries — detects regime shifts
Category: crypto
"""

FACTOR_NAME = "crypto_session_transition"
FACTOR_DESC = "Volatility change at major session boundaries (Asia/Europe/US)"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = volatility increasing at session boundary."""
    if idx < 24:
        return 0.5

    hour = idx % 24
    # Session boundaries: 0 (Asia open), 8 (Europe open), 14 (US open)
    is_boundary = hour in (0, 1, 8, 9, 14, 15)

    if not is_boundary:
        return 0.5

    # Compare volatility of last 4 bars vs previous 4 bars
    recent_vol = 0.0
    earlier_vol = 0.0
    for i in range(idx - 4, idx):
        if lows[i] > 0:
            recent_vol += (highs[i] - lows[i]) / lows[i]
    for i in range(idx - 8, idx - 4):
        if lows[i] > 0:
            earlier_vol += (highs[i] - lows[i]) / lows[i]

    if earlier_vol <= 0:
        return 0.5

    ratio = recent_vol / earlier_vol
    # ratio > 1 = volatility expanding, < 1 = contracting
    score = 0.5 + (ratio - 1.0) * 0.5
    return max(0.0, min(1.0, score))
