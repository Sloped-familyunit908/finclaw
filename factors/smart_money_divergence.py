"""
Auto-generated factor: smart_money_divergence
Description: Smart money divergence — price falling but big-volume bars are buying
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "smart_money_divergence"
FACTOR_DESC = "Smart money divergence — price falling but big-volume bars are buying"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Smart money divergence — price falling but big-volume bars are buying"""

    if idx < 20:
        return 0.5
    
    # Look at last 20 days
    # Find "big volume" days (above average)
    lookback = min(20, idx)
    avg_vol = sum(volumes[idx - lookback + 1:idx + 1]) / lookback
    
    if avg_vol <= 0:
        return 0.5
    
    # On big-volume days, what's the average price change?
    big_vol_changes = []
    normal_changes = []
    for i in range(idx - lookback + 1, idx + 1):
        if i < 1:
            continue
        change = (closes[i] - closes[i-1]) / closes[i-1] if closes[i-1] > 0 else 0
        if volumes[i] > avg_vol * 1.5:
            big_vol_changes.append(change)
        else:
            normal_changes.append(change)
    
    if not big_vol_changes or not normal_changes:
        return 0.5
    
    # Divergence: big-volume-day returns vs normal-day returns
    big_avg = sum(big_vol_changes) / len(big_vol_changes)
    normal_avg = sum(normal_changes) / len(normal_changes)
    
    # If big volume days are positive but normal days negative = smart money buying
    divergence = big_avg - normal_avg
    # -2% to +2% maps to 0 to 1
    score = (divergence + 0.02) / 0.04
    return max(0.0, min(1.0, score))

