"""
Auto-generated factor: volume_acceleration
Description: Volume acceleration — is volume growing faster than recently?
Category: microstructure
Generated: seed
"""

FACTOR_NAME = "volume_acceleration"
FACTOR_DESC = "Volume acceleration — is volume growing faster than recently?"
FACTOR_CATEGORY = "microstructure"


def compute(closes, highs, lows, volumes, idx):
    """Volume acceleration — is volume growing faster than recently?"""

    if idx < 10:
        return 0.5
    
    # Recent 5-day average volume
    vol_5 = sum(volumes[idx-4:idx+1]) / 5.0
    # Previous 5-day average (days -10 to -5)
    vol_prev5 = sum(volumes[idx-9:idx-4]) / 5.0
    
    if vol_prev5 <= 0:
        return 0.5
    
    accel = vol_5 / vol_prev5 - 1.0
    # -50% to +100% maps to 0 to 1
    score = (accel + 0.5) / 1.5
    return max(0.0, min(1.0, score))

