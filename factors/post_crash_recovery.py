"""
Auto-generated factor: post_crash_recovery
Description: Price dropped >15% in last 30 days but now recovering (>2% from low)
Category: fundamental_proxy
Generated: seed
"""

FACTOR_NAME = "post_crash_recovery"
FACTOR_DESC = "Price dropped >15% in last 30 days but now recovering (>2% from low)"
FACTOR_CATEGORY = "fundamental_proxy"


def compute(closes, highs, lows, volumes, idx):
    """Detect post-crash recovery: big drop + bounce from low."""

    lookback = 30
    if idx < lookback:
        return 0.5

    # Find max price and min price in lookback window
    max_price = closes[idx - lookback]
    min_price = closes[idx - lookback]
    min_idx = idx - lookback

    for i in range(idx - lookback, idx + 1):
        if closes[i] > max_price:
            max_price = closes[i]
        if closes[i] < min_price:
            min_price = closes[i]
            min_idx = i

    if max_price < 1e-10:
        return 0.5

    # Check for crash: >15% drop from peak
    crash_pct = (max_price - min_price) / max_price
    had_crash = crash_pct > 0.15

    if not had_crash:
        return 0.5

    # Check for recovery from low
    if min_price < 1e-10:
        return 0.5

    recovery_pct = (closes[idx] - min_price) / min_price

    # Recovery > 2% from low AND crash happened
    if recovery_pct > 0.02 and min_idx < idx:
        # More recovery = more bullish
        score = 0.6 + recovery_pct * 2.0
        return max(0.0, min(1.0, score))

    # Still at/near low after crash
    return 0.3
