"""
Factor: dispersion_signal
Description: Cross-sectional return dispersion proxy from single-stock data
Category: sentiment
"""

FACTOR_NAME = "dispersion_signal"
FACTOR_DESC = "Dispersion signal — return dispersion proxy indicating stock-picking environment quality"
FACTOR_CATEGORY = "sentiment"


def compute(closes, highs, lows, volumes, idx):
    """
    Cross-sectional return dispersion proxy.
    
    Since we only have single-stock data, we approximate "dispersion" by
    measuring the variance of rolling sub-period returns for this stock.
    
    High dispersion = high variance of returns across different windows
    = volatile, factor-driven environment (good for stock picking)
    
    Low dispersion = consistent returns across windows
    = macro-driven, everything moves together
    
    Score > 0.5 = high dispersion (factor strategies work better)
    Score < 0.5 = low dispersion (macro-driven, factor strategies struggle)
    """
    if idx < 20:
        return 0.5

    # Compute returns for multiple non-overlapping sub-periods
    sub_returns = []
    period_len = 5

    for start_offset in range(0, 20, period_len):
        end_idx = idx - start_offset
        start_idx = end_idx - period_len

        if start_idx < 0 or closes[start_idx] <= 0:
            continue

        ret = (closes[end_idx] - closes[start_idx]) / closes[start_idx]
        sub_returns.append(ret)

    if len(sub_returns) < 2:
        return 0.5

    # Compute variance of sub-period returns
    mean_ret = sum(sub_returns) / len(sub_returns)
    variance = 0.0
    for r in sub_returns:
        variance += (r - mean_ret) ** 2
    variance /= len(sub_returns)

    # Standard deviation of sub-returns
    dispersion = variance ** 0.5

    # Also compute range-based dispersion: daily high-low range variation
    ranges = []
    for i in range(idx - 19, idx + 1):
        if closes[i] > 0:
            day_range = (highs[i] - lows[i]) / closes[i]
            ranges.append(day_range)

    if len(ranges) >= 2:
        mean_range = sum(ranges) / len(ranges)
        range_var = 0.0
        for r in ranges:
            range_var += (r - mean_range) ** 2
        range_var /= len(ranges)
        range_dispersion = range_var ** 0.5
    else:
        range_dispersion = 0.0

    # Combine: return dispersion + range dispersion
    combined = dispersion * 0.7 + range_dispersion * 0.3

    # Normalize: 0-5% dispersion maps to 0-1
    score = min(combined / 0.05, 1.0)

    return max(0.0, min(1.0, score))
