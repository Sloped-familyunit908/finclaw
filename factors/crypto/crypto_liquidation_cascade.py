"""
Factor: crypto_liquidation_cascade
Description: Sudden >3% drop on >5x volume — cascade/liquidation event
Category: crypto
"""

FACTOR_NAME = "crypto_liquidation_cascade"
FACTOR_DESC = "Liquidation cascade detection — large drop with extreme volume"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = liquidation cascade detected (extreme bearish event)."""
    if idx < 48:
        return 0.5

    # Check for sudden drop
    if closes[idx - 1] <= 0:
        return 0.5

    drop = (closes[idx - 1] - closes[idx]) / closes[idx - 1]

    # Average volume over 48 bars
    avg_vol = sum(volumes[idx - 48:idx]) / 48
    if avg_vol <= 0:
        return 0.5

    vol_spike = volumes[idx] / avg_vol

    # Cascade: >3% drop AND >5x volume
    if drop > 0.03 and vol_spike > 5.0:
        # Severity scoring
        severity = min(drop / 0.10, 1.0) * 0.5 + min(vol_spike / 20.0, 1.0) * 0.5
        return max(0.0, min(1.0, severity))

    # Check over last 4 bars for multi-bar cascade
    total_drop = 0.0
    max_vol_spike = 0.0
    for i in range(idx - 3, idx + 1):
        if closes[i - 1] > 0:
            bar_drop = (closes[i - 1] - closes[i]) / closes[i - 1]
            if bar_drop > 0:
                total_drop += bar_drop
        if avg_vol > 0:
            max_vol_spike = max(max_vol_spike, volumes[i] / avg_vol)

    if total_drop > 0.03 and max_vol_spike > 3.0:
        severity = min(total_drop / 0.10, 1.0) * 0.5 + min(max_vol_spike / 15.0, 1.0) * 0.5
        return max(0.0, min(1.0, severity * 0.8))

    return 0.0  # No cascade
