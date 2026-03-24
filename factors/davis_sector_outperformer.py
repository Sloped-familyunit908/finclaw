"""
Davis Double Play factor: Sector Outperformer
Description: Identifies stocks significantly outperforming their price cohort.
Category: davis_double_play

Logic:
  In a Davis Double Play, the LEADER outperforms the sector:
  - 源杰科技 >> 世嘉科技 (both "光模块" but different quality)
  - 长飞光纤 >> 通鼎互联 (both "光纤" but different moat)

  Without sector classification data, we use a clever proxy:
  All factors receive the SAME stock data. But we can compare a stock's
  recent performance to its OWN historical average — stocks breaking out
  of their normal pattern are likely being re-rated.

  "Abnormal strength" = price doing something it hasn't done before.
  This captures the moment a stock transitions from boring to exciting.

  Concrete signals:
  1. 60d return is in the TOP percentile vs its own 1-year range
  2. Volume is at highs vs its own history
  3. New highs are being set (price discovery mode)

Generated: 2026-03-24
"""

FACTOR_NAME = "davis_sector_outperformer"
FACTOR_DESC = "Abnormal strength vs own history — sector leader identification"
FACTOR_CATEGORY = "davis_double_play"


def compute(closes, highs, lows, volumes, idx):
    """Detect stocks experiencing abnormal upward re-rating.

    Score components:
    1. Current price position in 250d range (close to 1yr high = breakout)
    2. Recent return vs historical return distribution
    3. Volume at extremes vs own history

    Returns 0-1 where >0.7 = likely sector outperformer.
    """
    # Use 250 trading days (~1 year) if available, else shorter
    yearly = min(idx, 250)
    if yearly < 60:
        return 0.5

    score = 0.0

    # --- 1. Price position in yearly range ---
    year_high = max(highs[idx - yearly:idx + 1])
    year_low = min(lows[idx - yearly:idx + 1])

    if year_high <= year_low:
        return 0.5

    price_position = (closes[idx] - year_low) / (year_high - year_low)
    # price_position = 1.0 means at yearly high (breakout)
    # price_position = 0.0 means at yearly low (not outperforming)

    if price_position > 0.90:
        score += 0.20  # At or near yearly high — price discovery!
    elif price_position > 0.75:
        score += 0.12
    elif price_position > 0.60:
        score += 0.05

    # --- 2. Return magnitude vs history ---
    # Is the recent 20d return exceptionally good vs what this stock normally does?
    if closes[idx - 20] <= 0:
        return 0.5
    recent_20d_return = (closes[idx] - closes[idx - 20]) / closes[idx - 20]

    # Calculate historical 20d returns for comparison
    historical_returns = []
    for j in range(max(20, idx - 240), idx - 20, 20):
        if j >= 20 and closes[j - 20] > 0:
            hr = (closes[j] - closes[j - 20]) / closes[j - 20]
            historical_returns.append(hr)

    if len(historical_returns) >= 3:
        avg_hist_return = sum(historical_returns) / len(historical_returns)
        sorted_returns = sorted(historical_returns)
        # Percentile rank of current return
        rank = sum(1 for r in sorted_returns if r < recent_20d_return)
        percentile = rank / len(sorted_returns)

        if percentile > 0.90:
            score += 0.15  # Top 10% of historical returns
        elif percentile > 0.75:
            score += 0.08
        elif percentile > 0.60:
            score += 0.03

    # --- 3. Volume surge vs own history ---
    if yearly >= 60:
        recent_avg_vol = sum(volumes[idx - 9:idx + 1]) / 10.0
        hist_avg_vol = sum(volumes[idx - yearly:idx - 10]) / max(1, yearly - 10)

        if hist_avg_vol > 0:
            vol_ratio = recent_avg_vol / hist_avg_vol
            if vol_ratio > 3.0:
                score += 0.10  # 3x normal volume — massive attention
            elif vol_ratio > 2.0:
                score += 0.07
            elif vol_ratio > 1.5:
                score += 0.04

    # --- 4. New high count (consecutive discovery) ---
    new_high_count = 0
    for i in range(idx - 19, idx + 1):
        if i > yearly:
            local_high = max(highs[i - yearly:i])
            if highs[i] >= local_high * 0.99:
                new_high_count += 1

    if new_high_count >= 5:
        score += 0.08  # Setting new highs frequently
    elif new_high_count >= 2:
        score += 0.04

    return max(0.0, min(1.0, 0.5 + score))
