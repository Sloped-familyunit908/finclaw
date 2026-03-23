"""
Factor: crypto_mean_revert_after_pump
Description: After detected pump, likelihood of mean reversion
Category: crypto
"""

FACTOR_NAME = "crypto_mean_revert_after_pump"
FACTOR_DESC = "Mean reversion probability after pump — how likely recent pump reverts"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = pump detected and reversion likely."""
    if idx < 48:
        return 0.5

    avg_vol = sum(volumes[idx - 48:idx]) / 48
    if avg_vol <= 0:
        return 0.5

    # Look for pump in last 12 bars
    pump_idx = -1
    pump_magnitude = 0.0
    for start in range(idx - 12, idx - 2):
        for end in range(start + 1, min(start + 5, idx)):
            if closes[start] <= 0:
                continue
            rise = (closes[end] - closes[start]) / closes[start]
            max_v = max(volumes[start:end + 1])
            if rise > 0.05 and max_v / avg_vol > 3.0:
                if rise > pump_magnitude:
                    pump_magnitude = rise
                    pump_idx = end

    if pump_idx < 0:
        return 0.5  # No recent pump

    # Check if reversion is happening after the pump
    if closes[pump_idx] <= 0:
        return 0.5

    pump_peak = max(highs[pump_idx:idx + 1])
    current_reversion = (pump_peak - closes[idx]) / pump_peak if pump_peak > 0 else 0

    # Score: how much of the pump has already reverted?
    if pump_magnitude > 0:
        revert_ratio = current_reversion / pump_magnitude
    else:
        revert_ratio = 0

    # Higher revert ratio = more reversion has occurred
    # But also: if reversion just started, signal that more likely coming
    bars_since_pump = idx - pump_idx
    time_factor = min(bars_since_pump / 12.0, 1.0)

    score = 0.5 + (revert_ratio * 0.3 + time_factor * 0.2)
    return max(0.0, min(1.0, score))
