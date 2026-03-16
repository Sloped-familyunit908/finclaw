"""Sector Rotation Strategy — rotate into strongest sectors based on momentum."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SectorSignal:
    """Signal for a single sector ETF."""
    symbol: str
    name: str
    score: float
    rank: int
    action: str  # 'buy', 'hold', 'sell'


class SectorRotation:
    """Rank and rotate across S&P 500 sector ETFs using momentum scoring.

    Uses relative momentum (lookback returns) with optional regime adjustment
    to identify the strongest sectors for capital allocation.
    """

    SECTORS = {
        'XLK': 'Technology',
        'XLF': 'Financials',
        'XLV': 'Healthcare',
        'XLE': 'Energy',
        'XLI': 'Industrials',
        'XLY': 'Consumer Disc.',
        'XLP': 'Consumer Staples',
        'XLU': 'Utilities',
        'XLRE': 'Real Estate',
        'XLC': 'Communication',
        'XLB': 'Materials',
    }

    # Regime preferences: which sectors tend to outperform in each regime
    REGIME_WEIGHTS = {
        'bull': {'XLK': 1.2, 'XLY': 1.2, 'XLF': 1.1, 'XLC': 1.1},
        'bear': {'XLP': 1.3, 'XLU': 1.3, 'XLV': 1.2, 'XLRE': 1.1},
        'volatile': {'XLE': 1.2, 'XLB': 1.1, 'XLP': 1.2, 'XLU': 1.1},
        'neutral': {},
    }

    def __init__(self, sectors: Optional[dict] = None):
        self.sectors = sectors or self.SECTORS

    def rank_sectors(self, data: dict, lookback: int = 63) -> list:
        """Rank sectors by momentum score over lookback period.

        Args:
            data: dict mapping sector symbol -> list of closing prices
            lookback: number of periods for momentum calculation (default 63 ~3 months)

        Returns:
            List of SectorSignal sorted by score descending
        """
        if lookback < 1:
            raise ValueError("lookback must be >= 1")

        scores = []
        for symbol, prices in data.items():
            if symbol not in self.sectors:
                continue
            if len(prices) < lookback + 1:
                continue

            # Momentum = return over lookback period
            recent = prices[-1]
            past = prices[-(lookback + 1)]
            if past == 0:
                continue
            momentum = (recent - past) / past

            # Smoothed momentum: average of full lookback and half lookback
            half = lookback // 2
            if len(prices) >= half + 1 and half > 0:
                past_half = prices[-(half + 1)]
                if past_half != 0:
                    mom_half = (recent - past_half) / past_half
                    score = (momentum + mom_half) / 2
                else:
                    score = momentum
            else:
                score = momentum

            scores.append((symbol, score))

        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (symbol, score) in enumerate(scores, 1):
            action = 'buy' if rank <= 3 else ('hold' if rank <= 6 else 'sell')
            results.append(SectorSignal(
                symbol=symbol,
                name=self.sectors[symbol],
                score=round(score, 6),
                rank=rank,
                action=action,
            ))
        return results

    def generate_signals(self, data: dict, top_n: int = 3) -> list:
        """Generate buy signals for the top N sectors.

        Args:
            data: dict mapping sector symbol -> list of closing prices
            top_n: number of top sectors to signal buy

        Returns:
            List of SectorSignal with action='buy' for top sectors
        """
        ranked = self.rank_sectors(data)
        signals = []
        for sig in ranked:
            if sig.rank <= top_n:
                sig.action = 'buy'
            else:
                sig.action = 'sell'
            signals.append(sig)
        return signals

    def regime_adjusted(self, data: dict, regime: str) -> list:
        """Rank sectors with regime-based weight adjustments.

        Args:
            data: dict mapping sector symbol -> list of closing prices
            regime: one of 'bull', 'bear', 'volatile', 'neutral'

        Returns:
            List of SectorSignal with regime-adjusted scores
        """
        if regime not in self.REGIME_WEIGHTS:
            raise ValueError(f"Unknown regime: {regime}. Use: {list(self.REGIME_WEIGHTS.keys())}")

        ranked = self.rank_sectors(data)
        weights = self.REGIME_WEIGHTS[regime]

        # Apply regime weights
        adjusted = []
        for sig in ranked:
            w = weights.get(sig.symbol, 1.0)
            adjusted.append(SectorSignal(
                symbol=sig.symbol,
                name=sig.name,
                score=round(sig.score * w, 6),
                rank=0,  # will re-rank
                action=sig.action,
            ))

        adjusted.sort(key=lambda x: x.score, reverse=True)
        for i, sig in enumerate(adjusted, 1):
            sig.rank = i
            sig.action = 'buy' if i <= 3 else ('hold' if i <= 6 else 'sell')

        return adjusted
