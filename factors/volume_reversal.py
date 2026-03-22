"""
Factor: volume_reversal
Description: Shrinking volume during decline, then sudden volume surge (reversal signal)
Category: volume
"""

FACTOR_NAME = "volume_reversal"
FACTOR_DESC = "Shrinking volume during decline, then sudden volume surge"
FACTOR_CATEGORY = "volume"


def compute(closes, highs, lows, volumes, idx):
    """Detect declining volume during price drop followed by volume spike."""
    if idx < 10:
        return 0.5

    # Check if we had a decline with shrinking volume in last 5 days
    decline_days = 0
    vol_shrinking = True
    for i in range(idx - 5, idx - 1):
        if closes[i] < closes[i - 1]:
            decline_days += 1
        if i > idx - 5 and volumes[i] > volumes[i - 1]:
            vol_shrinking = False

    # Today's volume vs 10-day average
    avg_vol = sum(volumes[idx - 9:idx + 1]) / 10
    if avg_vol <= 0:
        return 0.5

    vol_ratio = volumes[idx] / avg_vol

    # Today is up day with volume surge after decline with shrinking volume
    today_up = closes[idx] > closes[idx - 1]

    if decline_days >= 3 and vol_shrinking and vol_ratio > 1.5 and today_up:
        score = 0.7 + min((vol_ratio - 1.5) * 0.2, 0.3)
    elif decline_days >= 2 and vol_ratio > 1.5 and today_up:
        score = 0.6 + min((vol_ratio - 1.5) * 0.15, 0.2)
    elif today_up and vol_ratio > 1.5:
        score = 0.55
    else:
        score = 0.5

    return max(0.0, min(1.0, score))
