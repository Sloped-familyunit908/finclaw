"""
Factor: crypto_breakout_after_consolidation
Description: Consolidation followed by range expansion
Category: crypto
"""

FACTOR_NAME = "crypto_breakout_after_consolidation"
FACTOR_DESC = "Consolidation followed by range expansion"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = breakout after consolidation."""
    if idx < 25:
        return 0.5

    # Count narrow bars in preceding 24 bars (excl current)
    narrow = 0
    for i in range(idx - 24, idx - 1):
        if closes[i] <= 0:
            continue
        if (highs[i] - lows[i]) / closes[i] < 0.01:
            narrow += 1

    if narrow < 8:
        return 0.5

    # Check if current bar is expansion
    if closes[idx - 1] <= 0:
        return 0.5

    current_range = (highs[idx - 1] - lows[idx - 1]) / closes[idx - 1]
    avg_range = sum(
        (highs[i] - lows[i]) / closes[i] if closes[i] > 0 else 0
        for i in range(idx - 24, idx - 1)
    ) / 23

    if avg_range <= 0:
        return 0.5

    expansion = current_range / avg_range
    if expansion > 2.0:
        score = 0.5 + min((expansion - 2.0) * 0.1, 0.5)
        return max(0.0, min(1.0, score))

    return 0.5
