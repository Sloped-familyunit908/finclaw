"""
Factor: crypto_stop_hunt_pattern
Description: Quick wick below support then close above it
Category: crypto
"""

FACTOR_NAME = "crypto_stop_hunt_pattern"
FACTOR_DESC = "Quick wick below support then close above it"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = stop hunt pattern (bullish reversal)."""
    if idx < 25:
        return 0.5

    # Support = min close of last 24 bars excluding current
    support = min(closes[idx - 24:idx - 1])
    if support <= 0:
        return 0.5

    # Stop hunt: low pierces support, close above it
    low = lows[idx - 1]
    close = closes[idx - 1]
    high = highs[idx - 1]

    if low < support and close > support:
        pierce_depth = (support - low) / support
        recovery = (close - support) / support
        wick_ratio = (close - low) / (high - low) if high > low else 0

        if pierce_depth > 0.005 and wick_ratio > 0.6:
            score = 0.5 + min(pierce_depth * 20.0, 0.5)
            return max(0.0, min(1.0, score))

    return 0.5
