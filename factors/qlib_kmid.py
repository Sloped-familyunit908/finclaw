"""Qlib Alpha158 KMID: Intraday direction strength (close-open)/open."""
FACTOR_NAME = "qlib_kmid"
FACTOR_DESC = "Candlestick midpoint ratio: (close-open)/open — positive = bullish candle"
FACTOR_CATEGORY = "qlib_alpha158"


def compute(closes, highs, lows, volumes, idx):
    """Returns float in [0, 1]. 0.5 = doji, >0.5 = bullish, <0.5 = bearish."""
    if idx < 1:
        return 0.5

    open_price = closes[idx - 1]  # approximate open as previous close
    close_price = closes[idx]

    if open_price == 0:
        return 0.5

    kmid = (close_price - open_price) / open_price  # typically [-0.1, 0.1]

    # Normalize: clip to [-0.1, 0.1] then scale to [0, 1]
    kmid_clipped = max(-0.1, min(0.1, kmid))
    score = 0.5 + kmid_clipped * 5.0  # maps [-0.1, 0.1] -> [0, 1]

    return max(0.0, min(1.0, score))
