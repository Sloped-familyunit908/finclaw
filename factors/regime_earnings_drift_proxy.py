"""
Factor: earnings_drift_proxy
Description: Post-earnings announcement drift detection from price gaps
Category: sentiment
"""

FACTOR_NAME = "earnings_drift_proxy"
FACTOR_DESC = "Earnings drift proxy — detect large price gaps followed by continuation (PEAD anomaly)"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Post-Earnings Announcement Drift (PEAD) proxy.
    
    Look for large gap (>3%) followed by continuation in same direction.
    This is a well-documented anomaly where stocks continue to drift
    in the direction of an earnings surprise.
    
    Score > 0.5 = recent positive gap with continuation (bullish drift)
    Score < 0.5 = recent negative gap with continuation (bearish drift)
    Score = 0.5 = no significant gap detected
    """
    gap_threshold = 0.03  # 3% gap
    scan_window = 20  # look back up to 20 days

    if idx < scan_window:
        return 0.5

    best_drift_score = 0.5
    best_recency = 0.0

    for day_back in range(1, scan_window):
        gap_day = idx - day_back

        if gap_day < 1 or closes[gap_day - 1] <= 0:
            continue

        # Gap size: today's open proxy vs yesterday's close
        # Use (high + low) / 2 as open proxy since we don't have open
        gap_open_proxy = (highs[gap_day] + lows[gap_day]) / 2.0
        gap_pct = (gap_open_proxy - closes[gap_day - 1]) / closes[gap_day - 1]

        if abs(gap_pct) < gap_threshold:
            continue

        # Found a significant gap — check for continuation
        # Measure drift from gap day close to current close
        if closes[gap_day] <= 0:
            continue
        drift = (closes[idx] - closes[gap_day]) / closes[gap_day]

        # Gap and drift in same direction = PEAD
        same_direction = (gap_pct > 0 and drift > 0) or (gap_pct < 0 and drift < 0)

        if same_direction:
            # Strength based on gap magnitude and drift magnitude
            gap_strength = min(abs(gap_pct) / 0.10, 1.0)  # 3%-10% gap
            drift_strength = min(abs(drift) / 0.10, 1.0)   # up to 10% drift
            combined = (gap_strength + drift_strength) / 2.0

            # Recency decay
            recency = 1.0 - day_back / scan_window

            signal_strength = combined * recency

            if signal_strength > best_recency:
                best_recency = signal_strength
                if gap_pct > 0:
                    best_drift_score = 0.5 + combined * 0.5  # bullish drift
                else:
                    best_drift_score = 0.5 - combined * 0.5  # bearish drift

    return max(0.0, min(1.0, best_drift_score))
