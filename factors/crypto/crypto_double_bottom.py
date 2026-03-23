"""
Factor: crypto_double_bottom
Description: Two lows within 2% of each other in last 48 bars — reversal pattern
Category: crypto
"""

FACTOR_NAME = "crypto_double_bottom"
FACTOR_DESC = "Double bottom pattern detection — two similar lows in last 48 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = double bottom detected (bullish reversal)."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Find local minima (lows lower than neighbors)
    local_mins = []
    for i in range(idx - lookback + 2, idx - 1):
        if lows[i] <= lows[i - 1] and lows[i] <= lows[i + 1]:
            if lows[i] <= lows[i - 2] and i + 2 <= idx and lows[i] <= lows[i + 2]:
                local_mins.append((i, lows[i]))

    if len(local_mins) < 2:
        return 0.5

    # Check if any two minima are within 2% and separated by at least 8 bars
    for i in range(len(local_mins)):
        for j in range(i + 1, len(local_mins)):
            idx_a, low_a = local_mins[i]
            idx_b, low_b = local_mins[j]
            if abs(idx_b - idx_a) < 8:
                continue
            if low_a > 0:
                diff_pct = abs(low_a - low_b) / low_a
                if diff_pct < 0.02:
                    # Check if price has bounced between the two bottoms
                    mid_high = max(highs[idx_a:idx_b + 1])
                    bounce = (mid_high - low_a) / low_a if low_a > 0 else 0
                    # Current price near or above the bounce peak = confirmation
                    if closes[idx] > low_a:
                        strength = min(bounce * 10.0, 1.0)
                        score = 0.5 + strength * 0.4
                        return max(0.0, min(1.0, score))

    return 0.5
