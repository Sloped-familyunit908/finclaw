"""
Momentum Strategy (Jegadeesh & Titman, 1993)
Classic 12-1 month momentum: rank by past 12-month return, skip most recent month.
Long winners, short losers.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MomentumScore:
    symbol: str
    momentum_12m: float    # 12-month return
    momentum_skip1m: float # 12-1 month return (skip last month)
    rank: int = 0
    signal: str = "hold"


class MomentumJTStrategy:
    """
    Jegadeesh & Titman style cross-sectional momentum.
    
    For single-asset: use absolute momentum thresholds.
    For multi-asset: rank by 12-1 month return.
    """

    def __init__(
        self,
        lookback_months: int = 12,
        skip_months: int = 1,
        hold_months: int = 1,
        long_threshold: float = 0.10,  # 10% for absolute momentum
        short_threshold: float = -0.05,
        bars_per_month: int = 21,  # trading days per month
    ):
        self.lookback_months = lookback_months
        self.skip_months = skip_months
        self.hold_months = hold_months
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.bars_per_month = bars_per_month

    def score_single(self, prices: list[float]) -> MomentumScore:
        """Score a single asset's momentum."""
        total_bars_needed = (self.lookback_months + self.skip_months) * self.bars_per_month
        if len(prices) < total_bars_needed + 1:
            return MomentumScore(symbol="", momentum_12m=0, momentum_skip1m=0, signal="hold")

        skip_bars = self.skip_months * self.bars_per_month
        lookback_bars = self.lookback_months * self.bars_per_month

        # 12-month return
        p_now = prices[-1]
        p_12m = prices[-lookback_bars - skip_bars] if len(prices) > lookback_bars + skip_bars else prices[0]
        mom_12m = (p_now / p_12m) - 1

        # 12-1 month: skip last month
        p_1m = prices[-skip_bars] if len(prices) > skip_bars else p_now
        mom_skip = (p_1m / p_12m) - 1

        signal = "hold"
        if mom_skip > self.long_threshold:
            signal = "buy"
        elif mom_skip < self.short_threshold:
            signal = "sell"

        return MomentumScore(
            symbol="",
            momentum_12m=mom_12m,
            momentum_skip1m=mom_skip,
            signal=signal,
        )

    def rank_assets(self, asset_prices: dict[str, list[float]]) -> list[MomentumScore]:
        """Rank multiple assets by momentum. Top quintile = long, bottom = short."""
        scores = []
        for symbol, prices in asset_prices.items():
            s = self.score_single(prices)
            s.symbol = symbol
            scores.append(s)

        scores.sort(key=lambda x: x.momentum_skip1m, reverse=True)
        n = len(scores)
        quintile = max(n // 5, 1)

        for i, s in enumerate(scores):
            s.rank = i + 1
            if i < quintile:
                s.signal = "buy"     # top quintile
            elif i >= n - quintile:
                s.signal = "sell"    # bottom quintile
            else:
                s.signal = "hold"

        return scores
