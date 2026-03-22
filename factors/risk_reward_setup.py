"""
Auto-generated factor: risk_reward_setup
Description: Near support (low risk) with positive momentum (high reward potential)
Category: composite
Generated: seed
"""

FACTOR_NAME = "risk_reward_setup"
FACTOR_DESC = "Near support (low risk) with positive momentum (high reward potential)"
FACTOR_CATEGORY = "composite"


def compute(closes, highs, lows, volumes, idx):
    """Risk/reward setup: near support + positive momentum."""

    lookback = 20
    if idx < lookback:
        return 0.5

    # Find support level (recent low)
    min_low = lows[idx]
    for i in range(idx - lookback, idx):
        if lows[i] < min_low:
            min_low = lows[i]

    if min_low < 1e-10:
        return 0.5

    # Distance from support
    dist_from_support = (closes[idx] - min_low) / min_low

    # Near support: within 3% of low
    near_support = dist_from_support < 0.03

    # Positive momentum: 5-day return positive
    if idx >= 5:
        mom_5d = (closes[idx] - closes[idx - 5]) / closes[idx - 5] if closes[idx - 5] > 0 else 0.0
    else:
        mom_5d = 0.0

    positive_momentum = mom_5d > 0.005

    # RSI not deeply oversold (has room to bounce)
    if idx >= 14:
        gains = 0.0
        losses = 0.0
        for j in range(idx - 13, idx + 1):
            change = closes[j] - closes[j - 1]
            if change > 0:
                gains += change
            else:
                losses -= change
        avg_gain = gains / 14.0
        avg_loss = losses / 14.0
        if avg_loss < 1e-10:
            rsi = 100.0
        else:
            rsi = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    else:
        rsi = 50.0

    score = 0.5
    if near_support:
        score += 0.15
    if positive_momentum:
        score += 0.15
    if 30 < rsi < 60:
        score += 0.1

    if near_support and positive_momentum:
        score = max(score, 0.85)

    return max(0.0, min(1.0, score))
