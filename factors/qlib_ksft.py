"""Qlib Alpha158 KSFT: Price shift within candle (2*close-high-low)/open."""
FACTOR_NAME = "qlib_ksft"
FACTOR_DESC = "Candle shift: (2*close-high-low)/open — measures close position relative to range"
FACTOR_CATEGORY = "qlib_alpha158"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. >0.5 = close biased toward high, <0.5 = toward low."""
    if idx < 1:
        return 0.5

    close_price = closes[idx]
    high_price = highs[idx]
    low_price = lows[idx]
    open_price = closes[idx - 1]  # approximate open

    if open_price == 0:
        return 0.5

    ksft = (2.0 * close_price - high_price - low_price) / open_price

    # Typically in [-0.1, 0.1], normalize to [0, 1]
    ksft_clipped = max(-0.1, min(0.1, ksft))
    score = 0.5 + ksft_clipped * 5.0

    return max(0.0, min(1.0, score))
