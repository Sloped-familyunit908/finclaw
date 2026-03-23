"""
Factor: crypto_momentum_divergence
Description: New price highs but declining rate of change — bearish divergence
Category: crypto
"""

FACTOR_NAME = "crypto_momentum_divergence"
FACTOR_DESC = "New price highs with declining ROC — momentum divergence"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. Low = bearish divergence, High = bullish confirmation."""
    lookback = 24
    if idx < lookback:
        return 0.5

    # Check if current price is near recent high
    recent_high = max(highs[idx - lookback:idx + 1])
    if recent_high <= 0:
        return 0.5

    price_vs_high = closes[idx] / recent_high

    # Compute ROC at two points
    roc_period = 6
    if idx < roc_period * 2:
        return 0.5

    roc_current = (closes[idx] - closes[idx - roc_period]) / closes[idx - roc_period] if closes[idx - roc_period] > 0 else 0
    roc_prev = (closes[idx - roc_period] - closes[idx - roc_period * 2]) / closes[idx - roc_period * 2] if closes[idx - roc_period * 2] > 0 else 0

    # Bearish divergence: price near high but ROC declining
    if price_vs_high > 0.98:  # Price within 2% of recent high
        if roc_current < roc_prev and roc_prev > 0:
            # Divergence strength
            divergence = (roc_prev - roc_current) / max(abs(roc_prev), 0.001)
            strength = min(divergence / 2.0, 1.0)
            score = 0.5 - strength * 0.4
        elif roc_current > roc_prev:
            # Healthy momentum confirmation → bullish
            score = 0.5 + min(roc_current / 0.05, 1.0) * 0.3
        else:
            score = 0.5
    else:
        # Not near highs — check if near lows for bullish divergence
        recent_low = min(lows[idx - lookback:idx + 1])
        if recent_low > 0:
            price_vs_low = closes[idx] / recent_low
            if price_vs_low < 1.02 and roc_current > roc_prev:
                # Bullish divergence
                divergence = (roc_current - roc_prev) / max(abs(roc_prev), 0.001)
                strength = min(divergence / 2.0, 1.0)
                score = 0.5 + strength * 0.4
            else:
                score = 0.5
        else:
            score = 0.5

    return max(0.0, min(1.0, score))
