"""
Auto-generated factor: spring_pattern
Description: Price briefly breaks below support then quickly recovers above it (Wyckoff spring)
Category: composite
Generated: seed
"""

FACTOR_NAME = "spring_pattern"
FACTOR_DESC = "Price briefly breaks below support then quickly recovers above it (Wyckoff spring)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Detect Wyckoff spring: break below support then recover above."""

    lookback = 20
    if idx < lookback + 3:
        return 0.5

    # Define support as the lowest low in the prior lookback period (excluding last 3 days)
    support = lows[idx - lookback]
    for i in range(idx - lookback, idx - 3):
        if lows[i] < support:
            support = lows[i]

    if support < 1e-10:
        return 0.5

    # Check for spring: recent break below support then recovery
    broke_below = False
    recovered = False

    for i in range(idx - 3, idx + 1):
        if lows[i] < support:
            broke_below = True

    # Current close must be above support
    if broke_below and closes[idx] > support:
        recovered = True

    if broke_below and recovered:
        # How far above support did we recover?
        recovery_pct = (closes[idx] - support) / support
        # Volume on recovery day (buying interest)
        vol_total = 0.0
        for i in range(idx - lookback, idx):
            vol_total += volumes[i]
        avg_vol = vol_total / lookback
        vol_ratio = volumes[idx] / avg_vol if avg_vol > 0 else 1.0

        score = 0.7 + recovery_pct * 3.0
        if vol_ratio > 1.5:
            score += 0.1

        return max(0.0, min(1.0, score))

    return 0.5
