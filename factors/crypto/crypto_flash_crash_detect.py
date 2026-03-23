"""
Factor: crypto_flash_crash_detect
Description: >5% drop in <3 bars with >5x volume
Category: crypto
"""

FACTOR_NAME = "crypto_flash_crash_detect"
FACTOR_DESC = ">5% drop in <3 bars with >5x volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = flash crash detected."""
    if idx < 26:
        return 0.5

    avg_vol = sum(volumes[idx - 24:idx]) / 24
    if avg_vol <= 0 or closes[idx - 3] <= 0:
        return 0.5

    # Check if any 3-bar window ending at idx has >5% drop
    drop = (closes[idx - 1] - closes[idx - 3]) / closes[idx - 3]
    max_vol = max(volumes[idx - 3:idx])
    vol_spike = max_vol / avg_vol

    if drop < -0.05 and vol_spike > 5.0:
        severity = min(abs(drop) / 0.10, 1.0)
        return max(0.0, min(1.0, 0.5 + severity * 0.5))

    return 0.5
