"""
Factor: crypto_volume_sync
Description: Own volume vs dataset average volume correlation
Category: crypto
"""

FACTOR_NAME = "crypto_volume_sync"
FACTOR_DESC = "Volume synchronization — own volume pattern vs rolling mean"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Returns float in [0, 1].
    Measures whether volume is following its own trend (synchronized).
    High = volume increasing in sync with recent trend, Low = desynchronized.
    """
    lookback = 24
    if idx < lookback:
        return 0.5

    vol_window = volumes[idx - lookback:idx + 1]
    if len(vol_window) < lookback:
        return 0.5

    avg_vol = sum(vol_window) / len(vol_window)
    if avg_vol <= 0:
        return 0.5

    # Compute volume trend: linear regression slope proxy
    # Using simple correlation of volume with time index
    n = len(vol_window)
    mean_t = (n - 1) / 2.0
    mean_v = avg_vol

    cov_tv = sum((i - mean_t) * (vol_window[i] - mean_v) for i in range(n)) / n
    var_t = sum((i - mean_t) ** 2 for i in range(n)) / n

    if var_t <= 0:
        return 0.5

    # Normalized slope
    slope = cov_tv / var_t
    normalized_slope = slope / mean_v if mean_v > 0 else 0

    # Positive slope = volume increasing = synchronized activity
    # Map: slope -0.05 → 0, slope 0 → 0.5, slope +0.05 → 1.0
    score = 0.5 + normalized_slope / 0.1 * 0.5

    return max(0.0, min(1.0, score))
