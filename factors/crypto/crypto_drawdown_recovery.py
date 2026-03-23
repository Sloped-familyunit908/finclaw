"""
Factor: crypto_drawdown_recovery
Description: Speed of recovery after drawdown
Category: crypto
"""

FACTOR_NAME = "crypto_drawdown_recovery"
FACTOR_DESC = "Speed of drawdown recovery — fast recovery signals strength"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = recovering/recovered, Low = still in deep drawdown."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Find peak in lookback window
    peak = max(closes[idx - lookback:idx + 1])
    peak_idx = idx - lookback
    for i in range(idx - lookback, idx + 1):
        if closes[i] == peak:
            peak_idx = i
            break  # First occurrence

    if peak <= 0:
        return 0.5

    # Current drawdown from peak
    current_dd = (peak - closes[idx]) / peak

    # Find trough after peak
    if peak_idx >= idx:
        # Peak is current bar — no drawdown
        return 0.6

    trough = min(closes[peak_idx:idx + 1])
    max_dd = (peak - trough) / peak

    if max_dd < 0.01:
        # No significant drawdown
        return 0.55

    # Recovery ratio: how much of the drawdown has been recovered
    if max_dd > 0:
        recovery = 1.0 - (current_dd / max_dd)
    else:
        recovery = 1.0

    # Speed: bars since trough relative to bars of drawdown
    trough_idx = peak_idx
    for i in range(peak_idx, idx + 1):
        if closes[i] == trough:
            trough_idx = i

    recovery_bars = idx - trough_idx
    drawdown_bars = trough_idx - peak_idx

    if drawdown_bars > 0 and recovery_bars > 0:
        speed = drawdown_bars / recovery_bars  # >1 = fast recovery
        speed_factor = min(speed / 3.0, 1.0)
    else:
        speed_factor = 0.5

    # Combine recovery amount and speed
    score = recovery * 0.6 + speed_factor * 0.4

    return max(0.0, min(1.0, score))
