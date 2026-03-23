"""
Factor: crypto_aggressive_buyers
Description: Count of bars where close==high in last 24 — aggressive buying signal
Category: crypto
"""

FACTOR_NAME = "crypto_aggressive_buyers"
FACTOR_DESC = "Count of bars where close equals high in last 24 bars"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = many bars closing at highs (aggressive buyers)."""
    lookback = 24
    if idx < lookback:
        return 0.5

    count = 0
    for i in range(idx - lookback, idx):
        rng = highs[i] - lows[i]
        if rng > 0:
            # Close within 0.1% of high counts as "at high"
            if (highs[i] - closes[i]) / rng < 0.01:
                count += 1

    # Normalize: 0 aggressive bars → 0.5, max reasonable (~8/24) → 1.0
    score = 0.5 + (count / lookback) * 0.5 / 0.33  # scale so ~33% = 1.0
    return max(0.0, min(1.0, score))
