"""
Factor: crypto_risk_reward_setup
Description: Price position vs recent swing high/low — risk/reward ratio
Category: crypto
"""

FACTOR_NAME = "crypto_risk_reward_setup"
FACTOR_DESC = "Risk/reward setup based on price position vs recent swing points"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. High = good risk/reward for long, Low = good for short."""
    lookback = 48
    if idx < lookback:
        return 0.5

    # Find swing high and swing low in lookback
    swing_high = max(highs[idx - lookback:idx + 1])
    swing_low = min(lows[idx - lookback:idx + 1])

    total_range = swing_high - swing_low
    if total_range <= 0:
        return 0.5

    current = closes[idx]

    # Position in range: 0 = at swing low, 1 = at swing high
    position = (current - swing_low) / total_range

    # Near swing low = good risk/reward for long (high score)
    # Near swing high = good risk/reward for short (low score)
    # Add slight penalty for being at extremes (potential breakout)
    if position < 0.25:
        # Near support — good long setup
        score = 0.7 + (0.25 - position) * 0.8
    elif position > 0.75:
        # Near resistance — good short setup
        score = 0.3 - (position - 0.75) * 0.8
    else:
        # Mid-range — neutral
        score = 0.5

    return max(0.0, min(1.0, score))
