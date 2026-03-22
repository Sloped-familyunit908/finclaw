FACTOR_NAME = "gap_reversal"
FACTOR_DESC = "Gap down that reverses intraday — opens below prev close but closes above open"
FACTOR_CATEGORY = "gap_analysis"
LOOKBACK = 2

def compute(closes, highs, lows, volumes, idx):
    """Return float in [0.0, 1.0] where 1.0 = most bullish."""
    if idx < LOOKBACK:
        return 0.5
    prev_c = closes[idx - 1]
    if prev_c == 0:
        return 0.5
    # Gap down: today's high started below prev close (or close dropped then recovered)
    # Approximate: if low < prev_close and close > prev_close, it's a reversal
    if lows[idx] < prev_c and closes[idx] > prev_c:
        # Strong reversal — magnitude matters
        recovery = (closes[idx] - lows[idx]) / prev_c
        score = 0.5 + recovery * 5.0
        return max(0.0, min(1.0, score))
    elif lows[idx] < prev_c and closes[idx] > lows[idx]:
        # Partial reversal
        spread = highs[idx] - lows[idx]
        if spread == 0:
            return 0.5
        recovery_pct = (closes[idx] - lows[idx]) / spread
        score = 0.3 + recovery_pct * 0.3
        return max(0.0, min(1.0, score))
    return 0.5
