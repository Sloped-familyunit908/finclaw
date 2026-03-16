"""
Market Regime Detector
Detect market regimes (bull/bear/sideways/volatile) from return data.
Uses simple statistical methods for regime classification.
"""

import math
from dataclasses import dataclass


@dataclass
class RegimeState:
    regime: str
    confidence: float
    mean_return: float
    volatility: float


class RegimeDetector:
    """Detect market regimes from return series."""

    REGIMES = ('bull', 'bear', 'sideways', 'volatile')

    def __init__(
        self,
        bull_threshold: float = 0.02,
        bear_threshold: float = -0.02,
        vol_threshold: float = 0.05,
        lookback: int = 20,
    ):
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.vol_threshold = vol_threshold
        self.lookback = lookback

    def _stats(self, returns: list[float]) -> tuple[float, float]:
        if not returns:
            return 0.0, 0.0
        n = len(returns)
        mean = sum(returns) / n
        if n < 2:
            return mean, 0.0
        var = sum((r - mean) ** 2 for r in returns) / (n - 1)
        return mean, math.sqrt(var)

    def detect(self, returns: list[float]) -> str:
        """Detect current market regime.

        Args:
            returns: list of period returns (e.g. daily returns).

        Returns:
            One of 'bull', 'bear', 'sideways', 'volatile'.
        """
        if not returns:
            return 'sideways'

        window = returns[-self.lookback:] if len(returns) > self.lookback else returns
        mean, vol = self._stats(window)

        if vol > self.vol_threshold:
            return 'volatile'
        if mean > self.bull_threshold:
            return 'bull'
        if mean < self.bear_threshold:
            return 'bear'
        return 'sideways'

    def detect_detailed(self, returns: list[float]) -> RegimeState:
        """Detect regime with confidence and stats."""
        if not returns:
            return RegimeState(regime='sideways', confidence=0.0, mean_return=0.0, volatility=0.0)

        window = returns[-self.lookback:] if len(returns) > self.lookback else returns
        mean, vol = self._stats(window)
        regime = self.detect(returns)

        # Simple confidence based on how far from thresholds
        if regime == 'volatile':
            confidence = min(1.0, vol / (self.vol_threshold * 2))
        elif regime == 'bull':
            confidence = min(1.0, mean / (self.bull_threshold * 3))
        elif regime == 'bear':
            confidence = min(1.0, abs(mean) / (abs(self.bear_threshold) * 3))
        else:
            confidence = 1.0 - min(1.0, (abs(mean) / self.bull_threshold))

        return RegimeState(
            regime=regime,
            confidence=round(max(0, confidence), 4),
            mean_return=round(mean, 6),
            volatility=round(vol, 6),
        )

    def transition_matrix(self, returns: list[float]) -> dict:
        """Calculate regime transition probabilities.

        Splits returns into windows and tracks regime changes.

        Returns:
            {from_regime: {to_regime: probability}}
        """
        if len(returns) < self.lookback * 2:
            return {}

        regimes_seq = []
        for i in range(self.lookback, len(returns) + 1):
            window = returns[i - self.lookback:i]
            regimes_seq.append(self.detect(window))

        transitions: dict[str, dict[str, int]] = {r: {r2: 0 for r2 in self.REGIMES} for r in self.REGIMES}

        for i in range(1, len(regimes_seq)):
            transitions[regimes_seq[i - 1]][regimes_seq[i]] += 1

        # Convert to probabilities
        result = {}
        for from_r, to_dict in transitions.items():
            total = sum(to_dict.values())
            if total > 0:
                result[from_r] = {to_r: round(count / total, 4) for to_r, count in to_dict.items()}
            else:
                result[from_r] = {to_r: 0.0 for to_r in self.REGIMES}

        return result

    def regime_history(self, returns: list[float]) -> list[dict]:
        """Get regime classification for each lookback window.

        Returns:
            List of {index, regime, mean_return, volatility}.
        """
        history = []
        for i in range(self.lookback, len(returns) + 1):
            window = returns[i - self.lookback:i]
            mean, vol = self._stats(window)
            regime = self.detect(window)
            history.append({
                'index': i - 1,
                'regime': regime,
                'mean_return': round(mean, 6),
                'volatility': round(vol, 6),
            })
        return history

    def optimal_strategy(self, regime: str) -> str:
        """Suggest optimal strategy for a given regime.

        Args:
            regime: one of 'bull', 'bear', 'sideways', 'volatile'.

        Returns:
            Strategy recommendation string.
        """
        strategies = {
            'bull': 'trend_following — ride momentum with trailing stops',
            'bear': 'defensive — reduce exposure, hedge with stablecoins, DCA on dips',
            'sideways': 'grid_trading — capture range-bound oscillations',
            'volatile': 'reduce_size — smaller positions, wider stops, consider options hedging',
        }
        return strategies.get(regime, 'unknown regime')
