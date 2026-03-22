"""
Auto-generated factor: island_reversal
Description: Gap down then gap up (or vice versa) forming an island
Category: pattern
Generated: seed
"""

FACTOR_NAME = "island_reversal"
FACTOR_DESC = "Gap down then gap up (or vice versa) forming an island"
FACTOR_CATEGORY = "pattern"


def compute(closes, highs, lows, volumes, idx):
    """Detect island reversal: gap in one direction then gap back."""

    if idx < 5:
        return 0.5

    # Look for gap sequences in last few days
    # Gap down then gap up (bullish island reversal)
    for gap_day in range(idx - 3, idx):
        if gap_day < 1:
            continue
        # Gap down: high[gap_day] < low[gap_day - 1]
        gap_down = highs[gap_day] < lows[gap_day - 1]

        if gap_down:
            # Look for gap up after the island
            for recover_day in range(gap_day + 1, idx + 1):
                if recover_day < 1:
                    continue
                gap_up = lows[recover_day] > highs[recover_day - 1]
                if gap_up:
                    return 0.85  # Bullish island reversal

    # Gap up then gap down (bearish island reversal)
    for gap_day in range(idx - 3, idx):
        if gap_day < 1:
            continue
        gap_up = lows[gap_day] > highs[gap_day - 1]

        if gap_up:
            for recover_day in range(gap_day + 1, idx + 1):
                if recover_day < 1:
                    continue
                gap_down = highs[recover_day] < lows[recover_day - 1]
                if gap_down:
                    return 0.15  # Bearish island reversal

    return 0.5
