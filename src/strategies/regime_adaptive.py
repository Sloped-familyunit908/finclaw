"""
Regime-Adaptive Strategy — Automatically switch strategies based on detected market regime.

Uses regime detection (bull/bear/sideways) to route signal generation to the
most appropriate sub-strategy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RegimeSignal:
    """Signal from a regime-adaptive strategy."""
    signal: str          # buy, sell, hold
    confidence: float
    regime: str          # bull, bear, sideways
    strategy_used: str
    reason: str


class RegimeAdaptive:
    """Route signal generation to regime-specific strategies.

    Parameters
    ----------
    strategies : dict
        Mapping of regime name → strategy object.
        Each strategy must have ``generate_signal(prices) → obj.signal``.
        Keys should include some/all of: ``'bull'``, ``'bear'``, ``'sideways'``.
    sma_period : int
        SMA lookback for regime classification.
    vol_lookback : int
        Volatility lookback window.
    default_regime : str
        Fallback regime when detection is inconclusive.
    transition_smooth : int
        Bars a regime must persist before we switch (avoids whipsaw).
    """

    REGIMES = ('bull', 'bear', 'sideways')

    def __init__(
        self,
        strategies: Dict[str, Any],
        sma_period: int = 50,
        vol_lookback: int = 20,
        default_regime: str = 'sideways',
        transition_smooth: int = 3,
    ):
        self.strategies = strategies
        self.sma_period = sma_period
        self.vol_lookback = vol_lookback
        self.default_regime = default_regime
        self.transition_smooth = max(1, transition_smooth)
        self._regime_history: List[str] = []

    # ------------------------------------------------------------------
    # Regime detection
    # ------------------------------------------------------------------

    def detect_regime(self, data: List[float]) -> str:
        """Classify current market regime from price data.

        Uses SMA trend direction + realised volatility.
        """
        if len(data) < self.sma_period + 1:
            return self.default_regime

        prices = data[-self.sma_period - self.vol_lookback:]
        sma = sum(prices[-self.sma_period:]) / self.sma_period
        price = prices[-1]

        # Volatility
        if len(prices) >= self.vol_lookback + 1:
            rets = [(prices[i] / prices[i - 1]) - 1 for i in range(-self.vol_lookback, 0)]
            vol = math.sqrt(sum(r ** 2 for r in rets) / len(rets)) if rets else 0
        else:
            vol = 0

        # Trend strength
        trend = (price - sma) / sma if sma > 0 else 0

        # High vol → more cautious thresholds
        bull_threshold = 0.02 + vol * 0.5
        bear_threshold = -(0.02 + vol * 0.5)

        if trend > bull_threshold:
            raw_regime = 'bull'
        elif trend < bear_threshold:
            raw_regime = 'bear'
        else:
            raw_regime = 'sideways'

        # Smoothing: require persistence
        self._regime_history.append(raw_regime)
        if len(self._regime_history) > self.transition_smooth * 3:
            self._regime_history = self._regime_history[-self.transition_smooth * 3:]

        recent = self._regime_history[-self.transition_smooth:]
        if all(r == raw_regime for r in recent):
            return raw_regime

        # Not yet stable — keep previous regime if available
        if len(self._regime_history) > self.transition_smooth:
            prev = self._regime_history[-self.transition_smooth - 1]
            return prev
        return self.default_regime

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(self, data: List[float]) -> List[RegimeSignal]:
        """Generate trading signals using the regime-appropriate strategy.

        Returns a list with a single signal (current bar).
        """
        regime = self.detect_regime(data)
        strategy = self.strategies.get(regime)
        if strategy is None:
            # Fallback to default
            strategy = self.strategies.get(self.default_regime)
        if strategy is None:
            # Use first available
            strategy = next(iter(self.strategies.values()), None)

        strategy_name = type(strategy).__name__ if strategy else 'none'

        if strategy is None:
            return [RegimeSignal('hold', 0.0, regime, 'none', 'no strategy available')]

        # Delegate to sub-strategy
        sig = self._get_signal(strategy, data)
        confidence = self._regime_confidence(data)

        return [RegimeSignal(
            signal=sig,
            confidence=confidence,
            regime=regime,
            strategy_used=strategy_name,
            reason=f"Regime={regime}, delegated to {strategy_name}",
        )]

    def generate_signal(self, data: List[float]) -> RegimeSignal:
        """Convenience: return single signal."""
        signals = self.generate_signals(data)
        return signals[0] if signals else RegimeSignal('hold', 0.0, self.default_regime, 'none', 'empty')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_signal(self, strategy: Any, data: List[float]) -> str:
        """Extract signal string from a strategy object."""
        if hasattr(strategy, 'generate_signal'):
            result = strategy.generate_signal(data)
            if hasattr(result, 'signal'):
                return result.signal
            return str(result)
        if hasattr(strategy, 'signal'):
            val = strategy.signal(data)
            if isinstance(val, (int, float)):
                return 'buy' if val > 0.3 else ('sell' if val < -0.3 else 'hold')
        return 'hold'

    def _regime_confidence(self, data: List[float]) -> float:
        """Confidence in the detected regime (0-1)."""
        if len(data) < self.sma_period + 1:
            return 0.3
        sma = sum(data[-self.sma_period:]) / self.sma_period
        price = data[-1]
        trend = abs(price - sma) / sma if sma > 0 else 0
        # Stronger trend → higher confidence
        return min(1.0, 0.4 + trend * 10)

    def get_regime_stats(self) -> Dict[str, int]:
        """Return counts of each regime in history."""
        counts: Dict[str, int] = {r: 0 for r in self.REGIMES}
        for r in self._regime_history:
            counts[r] = counts.get(r, 0) + 1
        return counts
