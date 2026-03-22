"""
Factor: pullback_depth
Description: How deep is current pullback from recent high
Category: momentum
"""

FACTOR_NAME = "pullback_depth"
FACTOR_DESC = "Pullback depth from recent high — mild pullbacks are buying opportunities"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """
    Measure pullback from 20-day high.
    Shallow pullback (2-5%) in uptrend = bullish buying opportunity.
    Deep pullback (>15%) = bearish.
    """
    lookback = 20
    if idx < lookback:
        return 0.5

    recent_high = max(highs[idx - lookback + 1:idx + 1])
    if recent_high <= 0:
        return 0.5

    pullback_pct = (recent_high - closes[idx]) / recent_high

    # Check if we're in an uptrend (price higher than 20 days ago)
    uptrend = closes[idx] > closes[idx - lookback + 1]

    if uptrend:
        if pullback_pct < 0.02:
            # At or near highs
            score = 0.7
        elif pullback_pct < 0.05:
            # Mild pullback in uptrend = great buying opportunity
            score = 0.8
        elif pullback_pct < 0.10:
            # Moderate pullback
            score = 0.6
        else:
            # Deep pullback even in uptrend
            score = 0.45
    else:
        if pullback_pct < 0.05:
            score = 0.5
        elif pullback_pct < 0.10:
            score = 0.4
        elif pullback_pct < 0.20:
            score = 0.3
        else:
            # Very deep — oversold potential
            score = 0.35

    return max(0.0, min(1.0, score))
