"""
Davis Double Play factor: Volume-Price Sync
Description: Detects synchronized volume and price uptrend — the classic 量价齐升.
Category: davis_double_play

Logic:
  量价齐升 (volume-price sync rise) is THE classic Davis signal.
  When BOTH volume AND price trend up together:
  - Buyers are willing to pay MORE at HIGHER prices
  - More participants entering = genuine demand, not manipulation
  - This separates real trends from pump-and-dumps

  This differs from simple volume_breakout:
  - volume_breakout catches single-day spikes
  - This factor catches SUSTAINED multi-week synchronized trends

  Key distinction from existing factors:
  - volume_trend: only looks at volume direction
  - momentum_10d: only looks at price direction  
  - THIS: requires BOTH to trend together for weeks

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_volume_price_sync"
FACTOR_DESC = "Sustained volume-price synchronization — classic 量价齐升 signal"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect sustained volume-price sync (量价齐升).

    Scoring:
    1. Weekly volume trend (4 consecutive weeks)
    2. Weekly price trend (4 consecutive weeks)
    3. Sync bonus when both rise together
    4. Penalty when they diverge

    Returns 0-1 where >0.7 = strong sync signal.
    """
    lookback = 30
    if idx < lookback:
        return 0.5

    # --- Calculate weekly averages (4 weeks x 5 trading days) ---
    def _week_avg_vol(start, end):
        total = 0.0
        count = 0
        for i in range(start, end):
            total += volumes[i]
            count += 1
        return total / count if count > 0 else 0.0

    def _week_avg_price(start, end):
        total = 0.0
        count = 0
        for i in range(start, end):
            total += closes[i]
            count += 1
        return total / count if count > 0 else 0.0

    # 4 weeks of data
    w4_vol = _week_avg_vol(idx - 4, idx + 1)     # Most recent 5 days
    w3_vol = _week_avg_vol(idx - 9, idx - 4)
    w2_vol = _week_avg_vol(idx - 14, idx - 9)
    w1_vol = _week_avg_vol(idx - 19, idx - 14)    # Oldest 5 days

    w4_price = _week_avg_price(idx - 4, idx + 1)
    w3_price = _week_avg_price(idx - 9, idx - 4)
    w2_price = _week_avg_price(idx - 14, idx - 9)
    w1_price = _week_avg_price(idx - 19, idx - 14)

    if w1_vol <= 0 or w1_price <= 0:
        return 0.5

    # --- Count ascending weeks ---
    vol_ascending = 0
    price_ascending = 0
    sync_weeks = 0

    weekly_vols = [w1_vol, w2_vol, w3_vol, w4_vol]
    weekly_prices = [w1_price, w2_price, w3_price, w4_price]

    for i in range(1, 4):
        v_up = weekly_vols[i] > weekly_vols[i - 1]
        p_up = weekly_prices[i] > weekly_prices[i - 1]

        if v_up:
            vol_ascending += 1
        if p_up:
            price_ascending += 1
        if v_up and p_up:
            sync_weeks += 1

    score = 0.0

    # --- Sync scoring ---
    if sync_weeks == 3:
        score += 0.25  # Perfect 3-week sync — strongest signal
    elif sync_weeks == 2:
        score += 0.15  # Good sync
    elif sync_weeks == 1:
        score += 0.05  # Weak sync

    # --- Volume magnitude ---
    vol_growth = (w4_vol - w1_vol) / w1_vol
    if vol_growth > 1.0:
        score += 0.10  # Volume doubled over 4 weeks
    elif vol_growth > 0.5:
        score += 0.08
    elif vol_growth > 0.2:
        score += 0.04

    # --- Price magnitude ---
    price_growth = (w4_price - w1_price) / w1_price
    if price_growth > 0.15:
        score += 0.10  # Price up 15%+ over 4 weeks
    elif price_growth > 0.08:
        score += 0.06
    elif price_growth > 0.03:
        score += 0.03

    # --- Anti-pattern: volume up but price down = distribution ---
    if vol_ascending >= 2 and price_ascending <= 1:
        score -= 0.15  # Volume rising but price flat/down = selling into strength

    # --- Anti-pattern: price up but volume down = weak rally ---
    if price_ascending >= 2 and vol_ascending <= 0:
        score -= 0.10  # Price rising on declining volume = unsustainable

    return max(0.0, min(1.0, 0.5 + score))
