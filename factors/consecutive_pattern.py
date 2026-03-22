"""
Auto-generated factor: consecutive_pattern
Description: Consecutive up/down days with volume pattern — 3+ down days with declining volume = bullish reversal setup
Category: mean_reversion
Generated: seed
"""

FACTOR_NAME = "consecutive_pattern"
FACTOR_DESC = "Consecutive up/down days with volume pattern — 3+ down days with declining volume = bullish reversal setup"
FACTOR_CATEGORY = "mean_reversion"


def compute(closes, highs, lows, volumes, idx):
    """Consecutive up/down days with volume pattern — 3+ down days with declining volume = bullish reversal setup"""

    if idx < 5:
        return 0.5
    
    # Count consecutive down days
    down_days = 0
    vol_declining = True
    for i in range(idx, max(idx - 10, 0), -1):
        if i < 1:
            break
        if closes[i] < closes[i-1]:
            down_days += 1
            if i > 1 and volumes[i] > volumes[i-1]:
                vol_declining = False
        else:
            break
    
    # Count consecutive up days
    up_days = 0
    for i in range(idx, max(idx - 10, 0), -1):
        if i < 1:
            break
        if closes[i] > closes[i-1]:
            up_days += 1
        else:
            break
    
    # 3+ down days with declining volume = reversal setup (bullish)
    if down_days >= 3 and vol_declining:
        score = min(0.7 + down_days * 0.05, 1.0)
    elif down_days >= 3:
        score = 0.6
    elif up_days >= 3:
        score = 0.3  # extended up, less bullish
    else:
        score = 0.5
    
    return max(0.0, min(1.0, score))

