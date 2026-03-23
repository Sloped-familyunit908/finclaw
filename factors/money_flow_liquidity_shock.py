"""
Factor: liquidity_shock
Description: Sudden volume spike (>3x 20-day avg) with significant price move
Category: flow
"""

FACTOR_NAME = "liquidity_shock"
FACTOR_DESC = "Liquidity shock — sudden volume spike with price move, often precedes continuation"
FACTOR_CATEGORY = "flow"


def compute(closes, highs, lows, volumes, idx):
    """
    Liquidity shock: detect sudden volume spike (>3x 20-day avg) with price move.
    
    Score based on recency and magnitude of the shock.
    A bullish shock (spike + positive move) = high score.
    A bearish shock (spike + negative move) = low score.
    No recent shock = neutral 0.5.
    """
    vol_window = 20
    scan_window = 5  # look back up to 5 days for recent shocks

    if idx < vol_window + 1:
        return 0.5

    best_shock_score = 0.0
    best_recency = 0.0

    for day_offset in range(scan_window):
        check_idx = idx - day_offset
        if check_idx < vol_window + 1:
            continue

        # Compute 20-day average volume BEFORE the check day
        vol_sum = 0.0
        for i in range(check_idx - vol_window, check_idx):
            vol_sum += volumes[i]
        avg_vol = vol_sum / vol_window

        if avg_vol <= 0:
            continue

        vol_ratio = volumes[check_idx] / avg_vol

        if vol_ratio < 3.0:
            continue

        # This is a liquidity shock
        # Daily price change
        if closes[check_idx - 1] <= 0:
            continue
        price_change_pct = (closes[check_idx] - closes[check_idx - 1]) / closes[check_idx - 1]

        # Magnitude of shock (volume ratio above 3x)
        vol_magnitude = min((vol_ratio - 3.0) / 5.0, 1.0)  # 3x-8x maps to 0-1

        # Direction: positive price change with shock = bullish continuation
        if price_change_pct > 0:
            shock_signal = 0.5 + vol_magnitude * 0.5  # 0.5 to 1.0
        else:
            shock_signal = 0.5 - vol_magnitude * 0.5  # 0.0 to 0.5

        # Recency: today's shock matters more than 5 days ago
        recency_weight = 1.0 - day_offset * 0.15

        shock_score = abs(shock_signal - 0.5) * recency_weight
        if shock_score > best_shock_score:
            best_shock_score = shock_score
            best_recency = shock_signal

    if best_shock_score == 0.0:
        return 0.5

    return max(0.0, min(1.0, best_recency))
