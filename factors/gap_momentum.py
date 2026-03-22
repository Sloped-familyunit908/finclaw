"""
Auto-generated factor: gap_momentum
Description: Gap-up/gap-down momentum — measures if stock opened above/below previous close
Category: momentum
Generated: seed
"""

FACTOR_NAME = "gap_momentum"
FACTOR_DESC = "Gap-up/gap-down momentum — measures if stock opened above/below previous close"
FACTOR_CATEGORY = "momentum"


def compute(closes, highs, lows, volumes, idx):
    """Gap-up/gap-down momentum — measures if stock opened above/below previous close"""

    if idx < 1:
        return 0.5
    
    # Gap = (today's open - yesterday's close) / yesterday's close
    prev_close = closes[idx - 1]
    if prev_close <= 0:
        return 0.5
    
    # We don't have opens directly, approximate from close/high/low
    # Use (high + low) / 2 as rough open proxy
    today_mid = (highs[idx] + lows[idx]) / 2.0
    gap_pct = (today_mid - prev_close) / prev_close
    
    # Normalize: -3% to +3% maps to 0.0 to 1.0
    score = (gap_pct + 0.03) / 0.06
    return max(0.0, min(1.0, score))

