"""
Davis Double Play factor: Revenue Acceleration
Description: Detects accelerating revenue growth — the core demand signal.
Category: davis_double_play

Logic:
  When a company's revenue growth is ACCELERATING (not just growing, but growing faster),
  it signals that new demand is pouring in — the single most important Davis Double Play signal.

  Using price as a proxy when fundamental data isn't available:
  - Price acceleration over 60d vs 20d (recent growth faster than older growth)
  - Volume confirmation (more volume = more buyer interest = demand)
  - Combined with trend strength

  This is the #1 weighted factor in the Davis framework per 老板's insight:
  "没有需求，你再出清也没有用" — without demand, supply cleanup is worthless.

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_revenue_acceleration"
FACTOR_DESC = "Revenue/price growth acceleration — demand explosion signal"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect accelerating growth — price acceleration as demand proxy.

    Score breakdown:
      - Recent 20d return vs prior 40d return: is growth accelerating?
      - Volume trend: is buying interest increasing?
      - Price above key MAs: confirming sustained demand

    Returns 0-1 where >0.7 = strong acceleration signal.
    """
    lookback = 60
    if idx < lookback:
        return 0.5

    # --- Growth acceleration ---
    # Recent 20d return
    if closes[idx - 20] <= 0:
        return 0.5
    recent_return = (closes[idx] - closes[idx - 20]) / closes[idx - 20]

    # Prior period 20d return (20-40 days ago)
    if closes[idx - 40] <= 0:
        return 0.5
    prior_return = (closes[idx - 20] - closes[idx - 40]) / closes[idx - 40]

    # Oldest period 20d return (40-60 days ago)
    if closes[idx - 60] <= 0:
        return 0.5
    oldest_return = (closes[idx - 40] - closes[idx - 60]) / closes[idx - 60]

    # Acceleration = recent growth > prior growth > oldest growth
    # All three periods positive AND accelerating = strongest signal
    accel_score = 0.0

    if recent_return > 0 and prior_return > 0 and oldest_return > 0:
        # Triple positive — sustained growth
        accel_score += 0.15
        if recent_return > prior_return > oldest_return:
            # Perfect acceleration pattern
            accel_score += 0.25
        elif recent_return > prior_return:
            # Accelerating but not perfectly
            accel_score += 0.15
    elif recent_return > 0 and prior_return > 0:
        # Two periods positive
        accel_score += 0.08
        if recent_return > prior_return:
            accel_score += 0.10
    elif recent_return > 0:
        # Only recent period positive — inflection?
        accel_score += 0.05

    # --- Volume acceleration (demand confirmation) ---
    recent_vol = 0.0
    prior_vol = 0.0
    for i in range(idx - 9, idx + 1):
        recent_vol += volumes[i]
    for i in range(idx - 29, idx - 19):
        prior_vol += volumes[i]

    if prior_vol > 0:
        vol_accel = recent_vol / prior_vol
        if vol_accel > 1.5:
            accel_score += 0.15  # Volume surging
        elif vol_accel > 1.2:
            accel_score += 0.10  # Volume increasing
        elif vol_accel > 1.0:
            accel_score += 0.05  # Slight increase

    # --- Trend confirmation (MA alignment) ---
    ma5 = sum(closes[idx - 4:idx + 1]) / 5.0
    ma10 = sum(closes[idx - 9:idx + 1]) / 10.0
    ma20 = sum(closes[idx - 19:idx + 1]) / 20.0

    if closes[idx] > ma5 > ma10 > ma20:
        accel_score += 0.10  # Perfect bullish alignment

    # Clamp to [0, 1]
    return max(0.0, min(1.0, 0.5 + accel_score))
