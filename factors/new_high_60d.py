"""
Auto-generated factor: new_high_60d
Description: Is price at 60-day high? (strong momentum)
Category: relative_strength
Generated: seed
"""

FACTOR_NAME = "new_high_60d"
FACTOR_DESC = "Is price at 60-day high? (strong momentum)"
FACTOR_CATEGORY = "relative_strength"


def compute(closes, highs, lows, volumes, idx):
    """Check if current price is at or near 60-day high."""

    lookback = 60
    if idx < lookback:
        return 0.5

    # Find 60-day high
    max_high = highs[idx - lookback]
    for i in range(idx - lookback, idx + 1):
        if highs[i] > max_high:
            max_high = highs[i]

    if max_high < 1e-10:
        return 0.5

    # How close to 60-day high
    proximity = closes[idx] / max_high

    if proximity >= 0.99:
        return 0.95  # At new high
    elif proximity >= 0.95:
        return 0.75  # Near high
    elif proximity >= 0.90:
        return 0.6
    elif proximity >= 0.80:
        return 0.45
    else:
        return 0.3
