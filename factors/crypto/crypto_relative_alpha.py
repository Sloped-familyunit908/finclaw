"""
Factor: crypto_relative_alpha
Description: Return vs equal-weight average return — alpha generation
Category: crypto
"""

FACTOR_NAME = "crypto_relative_alpha"
FACTOR_DESC = "Relative alpha — own return vs rolling average performance"
FACTOR_CATEGORY = "crypto"


def compute(closes, highs, lows, volumes, idx):
    """
    Returns float in [0, 1].
    Measures own recent return relative to a rolling benchmark.
    High = outperforming, Low = underperforming.
    """
    short_period = 12
    long_period = 48
    if idx < long_period:
        return 0.5

    if closes[idx - short_period] <= 0 or closes[idx - long_period] <= 0:
        return 0.5

    # Short-term return
    ret_short = (closes[idx] - closes[idx - short_period]) / closes[idx - short_period]

    # Long-term average return (as benchmark)
    ret_long = (closes[idx] - closes[idx - long_period]) / closes[idx - long_period]
    # Annualize to per-period: long avg per bar
    avg_ret_per_bar = ret_long / long_period
    expected_short_ret = avg_ret_per_bar * short_period

    # Alpha = actual short return - expected return
    alpha = ret_short - expected_short_ret

    # Map alpha: -5% → 0, 0% → 0.5, +5% → 1.0
    score = 0.5 + alpha / 0.1 * 0.5

    return max(0.0, min(1.0, score))
