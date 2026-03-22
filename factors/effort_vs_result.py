FACTOR_NAME = "effort_vs_result"
FACTOR_DESC = "Volume (effort) vs price change (result) — high volume + small move = reversal signal"
FACTOR_CATEGORY = "wyckoff_vsa"
LOOKBACK = 20

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    # Average volume
    avg_vol = sum(volumes[idx - LOOKBACK + 1:idx + 1]) / LOOKBACK
    if avg_vol == 0:
        return 0.5
    vol_ratio = volumes[idx] / avg_vol
    # Price change (spread)
    spread = abs(closes[idx] - closes[idx - 1]) / closes[idx - 1] if closes[idx - 1] != 0 else 0
    avg_spread = 0.0
    count = 0
    for i in range(idx - LOOKBACK + 1, idx + 1):
        if i > 0 and closes[i - 1] != 0:
            avg_spread += abs(closes[i] - closes[i - 1]) / closes[i - 1]
            count += 1
    if count > 0:
        avg_spread /= count
    if avg_spread == 0:
        return 0.5
    spread_ratio = spread / avg_spread
    # High effort (volume) + low result (spread) = divergence
    if vol_ratio > 1.5 and spread_ratio < 0.5:
        # Strong divergence — direction depends on price direction
        if closes[idx] < closes[idx - 1]:
            # High vol down bar with small move = stopping action = bullish
            score = 0.8
        else:
            # High vol up bar with small move = exhaustion = bearish
            score = 0.3
    else:
        score = 0.5
    return max(0.0, min(1.0, score))
