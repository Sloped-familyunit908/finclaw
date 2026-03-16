"""Signal Combiner — merge signals from multiple strategies with weighted voting."""

import itertools
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class Strategy(Protocol):
    """Protocol for strategies that produce signals."""
    def generate_signal(self, data) -> dict:
        """Return dict with at least 'signal' (-1, 0, 1) and 'confidence' (0-1)."""
        ...


@dataclass
class CombinedSignal:
    """Result of combining multiple strategy signals."""
    signal: float  # weighted signal (-1 to 1)
    confidence: float  # 0 to 1
    contributing: list  # list of strategy names that contributed


class SignalCombiner:
    """Combine signals from multiple strategies with weighted voting.

    Each strategy is expected to implement generate_signal(data) -> dict
    returning at least {'signal': float, 'confidence': float}.
    """

    def __init__(self, strategies: list, weights: Optional[list] = None):
        """
        Args:
            strategies: list of (name, strategy_object) tuples
            weights: optional weights for each strategy (default: equal)
        """
        if not strategies:
            raise ValueError("At least one strategy required")

        self.strategies = strategies
        if weights is None:
            self.weights = [1.0 / len(strategies)] * len(strategies)
        else:
            if len(weights) != len(strategies):
                raise ValueError("weights length must match strategies length")
            total = sum(weights)
            self.weights = [w / total for w in weights] if total > 0 else [0.0] * len(weights)

    def combine(self, data) -> dict:
        """Combine all strategy signals into a weighted consensus.

        Args:
            data: market data passed to each strategy

        Returns:
            dict with 'signal' (weighted avg), 'confidence', 'contributing' strategies
        """
        weighted_signal = 0.0
        weighted_confidence = 0.0
        contributing = []

        for (name, strategy), weight in zip(self.strategies, self.weights):
            try:
                result = strategy.generate_signal(data)
                sig = result.get('signal', 0)
                conf = result.get('confidence', 0.5)
                weighted_signal += sig * weight
                weighted_confidence += conf * weight
                if sig != 0:
                    contributing.append(name)
            except Exception:
                # Strategy failed, skip it
                continue

        # Clamp
        weighted_signal = max(-1.0, min(1.0, weighted_signal))
        weighted_confidence = max(0.0, min(1.0, weighted_confidence))

        return {
            'signal': round(weighted_signal, 6),
            'confidence': round(weighted_confidence, 6),
            'contributing': contributing,
        }

    def optimize_weights(self, data_series: list, metric: str = 'sharpe') -> list:
        """Brute-force optimize weights by testing combinations on historical data.

        Args:
            data_series: list of data snapshots to evaluate
            metric: 'sharpe' or 'returns'

        Returns:
            Optimized weights list
        """
        if len(self.strategies) > 5:
            # Too many combos; use simple scoring approach
            return self._score_based_optimize(data_series, metric)

        n = len(self.strategies)
        best_weights = list(self.weights)
        best_score = float('-inf')

        # Grid search with 0.1 step
        steps = [round(i * 0.1, 1) for i in range(11)]
        for combo in itertools.product(steps, repeat=n):
            total = sum(combo)
            if total == 0:
                continue
            weights = [w / total for w in combo]

            score = self._evaluate_weights(weights, data_series, metric)
            if score > best_score:
                best_score = score
                best_weights = weights

        self.weights = best_weights
        return [round(w, 4) for w in best_weights]

    def _evaluate_weights(self, weights: list, data_series: list, metric: str) -> float:
        """Evaluate a set of weights on historical data."""
        original_weights = self.weights
        self.weights = weights

        signals = []
        for data in data_series:
            result = self.combine(data)
            signals.append(result['signal'])

        self.weights = original_weights

        if not signals:
            return 0.0

        if metric == 'returns':
            return sum(signals)

        # Sharpe-like: mean / std
        mean = sum(signals) / len(signals)
        if len(signals) < 2:
            return mean
        variance = sum((s - mean) ** 2 for s in signals) / (len(signals) - 1)
        std = variance ** 0.5
        return mean / std if std > 0 else mean

    def _score_based_optimize(self, data_series: list, metric: str) -> list:
        """Score each strategy individually and weight by performance."""
        scores = []
        for i, (name, strategy) in enumerate(self.strategies):
            individual_weights = [0.0] * len(self.strategies)
            individual_weights[i] = 1.0
            score = self._evaluate_weights(individual_weights, data_series, metric)
            scores.append(max(score, 0))

        total = sum(scores)
        if total == 0:
            return list(self.weights)

        self.weights = [s / total for s in scores]
        return [round(w, 4) for w in self.weights]
