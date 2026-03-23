"""
Factor: crypto_pump_detection
Description: >5% rise in <4 candles with >3x volume — pump event detection
Category: crypto
"""

FACTOR_NAME = "crypto_pump_detection"
FACTOR_DESC = "Pump event detection — rapid price rise with high volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = pump event detected."""
    if idx < 48:
        return 0.5

    avg_vol = sum(volumes[idx - 48:idx]) / 48
    if avg_vol <= 0:
        return 0.5

    # Check various windows (1-4 bars) for rapid rise
    for window in range(1, 5):
        if idx < window:
            continue
        if closes[idx - window] <= 0:
            continue

        rise = (closes[idx] - closes[idx - window]) / closes[idx - window]
        max_vol = max(volumes[idx - window:idx + 1])
        vol_spike = max_vol / avg_vol

        if rise > 0.05 and vol_spike > 3.0:
            # Pump detected — score by intensity
            intensity = min(rise / 0.15, 1.0) * 0.5 + min(vol_spike / 10.0, 1.0) * 0.5
            return max(0.0, min(1.0, intensity))

    # Check for moderate pump
    if closes[idx - 4] > 0:
        rise_4 = (closes[idx] - closes[idx - 4]) / closes[idx - 4]
        max_vol_4 = max(volumes[idx - 4:idx + 1])
        vol_ratio = max_vol_4 / avg_vol

        if rise_4 > 0.03 and vol_ratio > 2.0:
            return 0.4  # Mild pump signal

    return 0.0  # No pump
