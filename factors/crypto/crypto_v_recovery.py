"""
Factor: crypto_v_recovery
Description: Flash crash followed by >50% recovery within 6 bars
Category: crypto
"""

FACTOR_NAME = "crypto_v_recovery"
FACTOR_DESC = "Flash crash followed by >50% recovery within 6 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = V-shaped recovery detected."""
    if idx < 12:
        return 0.5

    # Look for a low point in last 6 bars that was a crash
    min_low = min(lows[idx - 6:idx])
    min_idx = idx - 6
    for i in range(idx - 6, idx):
        if lows[i] == min_low:
            min_idx = i
            break

    # Need price before crash
    pre_crash_idx = max(0, min_idx - 3)
    if closes[pre_crash_idx] <= 0:
        return 0.5

    crash_depth = (min_low - closes[pre_crash_idx]) / closes[pre_crash_idx]
    if crash_depth >= -0.03:
        return 0.5

    recovery = (closes[idx - 1] - min_low) / (closes[pre_crash_idx] - min_low) if closes[pre_crash_idx] > min_low else 0

    if recovery > 0.5:
        score = 0.5 + min(recovery - 0.5, 0.5)
        return max(0.0, min(1.0, score))

    return 0.5
