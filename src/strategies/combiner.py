"""
Strategy Combiner
Combine multiple strategies with configurable weights to produce a unified signal.
"""

from dataclasses import dataclass, field
from typing import Protocol, Any, Optional
import math


class StrategyProtocol(Protocol):
    """Any strategy that can produce a signal from price data."""
    def signal(self, prices: list[float]) -> float: ...


@dataclass
class CombinedSignal:
    """Result of combining multiple strategy signals."""
    value: float          # -1 (strong sell) to 1 (strong buy)
    components: dict[str, float]  # individual strategy signals
    weights: dict[str, float]     # normalized weights
    confidence: float     # agreement among strategies (0 to 1)
    regime: str           # bull, bear, neutral
    suggested_position: str  # long, short, flat


class StrategyCombiner:
    """
    Combine multiple strategies with configurable weights.
    
    Each strategy must have a .signal(prices) -> float method 
    returning a value in [-1, 1].
    
    Wrapper adapters are provided for existing FinClaw strategies.
    """

    def __init__(
        self,
        strategies: list[Any],
        weights: Optional[list[float]] = None,
        names: Optional[list[str]] = None,
    ):
        if len(strategies) == 0:
            raise ValueError("At least one strategy required")
        self.strategies = strategies
        n = len(strategies)
        raw_weights = weights if weights else [1.0] * n
        if len(raw_weights) != n:
            raise ValueError(f"Expected {n} weights, got {len(raw_weights)}")
        total = sum(abs(w) for w in raw_weights) or 1.0
        self._weights = [w / total for w in raw_weights]
        self._names = names or [
            getattr(s, '__class__', type(s)).__name__ for s in strategies
        ]

    def signal(self, prices: list[float]) -> float:
        """Return combined signal in [-1, 1]."""
        total = 0.0
        for strat, w in zip(self.strategies, self._weights):
            total += strat.signal(prices) * w
        return max(-1.0, min(1.0, total))

    def detailed_signal(self, prices: list[float]) -> CombinedSignal:
        """Return detailed combined signal with component breakdown."""
        components = {}
        for strat, name in zip(self.strategies, self._names):
            components[name] = strat.signal(prices)

        weighted_sum = sum(
            components[name] * w
            for name, w in zip(self._names, self._weights)
        )
        combined = max(-1.0, min(1.0, weighted_sum))

        # Confidence: how much strategies agree (1 = all agree, 0 = conflicting)
        vals = list(components.values())
        if len(vals) > 1:
            signs = [1 if v > 0.05 else (-1 if v < -0.05 else 0) for v in vals]
            agreement = abs(sum(signs)) / len(signs)
            spread = max(vals) - min(vals)
            confidence = max(0.0, agreement * (1.0 - spread / 2.0))
        else:
            confidence = abs(combined)

        if combined > 0.2:
            regime = "bull"
        elif combined < -0.2:
            regime = "bear"
        else:
            regime = "neutral"

        if combined > 0.15:
            position = "long"
        elif combined < -0.15:
            position = "short"
        else:
            position = "flat"

        return CombinedSignal(
            value=combined,
            components=components,
            weights=dict(zip(self._names, self._weights)),
            confidence=confidence,
            regime=regime,
            suggested_position=position,
        )


# ── Adapters for existing FinClaw strategies ──


class MeanReversionAdapter:
    """Wrap MeanReversionStrategy to produce a signal float."""
    def __init__(self, strategy):
        self.strategy = strategy

    def signal(self, prices: list[float]) -> float:
        sig = self.strategy.generate_signal(prices)
        if sig.signal == "buy":
            return sig.confidence
        elif sig.signal == "sell":
            return -sig.confidence
        return 0.0


class MomentumAdapter:
    """Wrap MomentumJTStrategy to produce a signal float."""
    def __init__(self, strategy):
        self.strategy = strategy

    def signal(self, prices: list[float]) -> float:
        score = self.strategy.score_single(prices)
        if score.signal == "buy":
            return min(1.0, max(0.3, score.momentum_skip1m * 2))
        elif score.signal == "sell":
            return max(-1.0, min(-0.3, score.momentum_skip1m * 2))
        return score.momentum_skip1m


class TrendFollowingAdapter:
    """Wrap TrendFollowingStrategy to produce a signal float."""
    def __init__(self, strategy):
        self.strategy = strategy

    def signal(self, prices: list[float]) -> float:
        sig = self.strategy.generate_signal(prices)
        if sig.signal == "buy":
            return sig.confidence
        elif sig.signal == "sell":
            return -sig.confidence
        return 0.0


class ValueMomentumAdapter:
    """Wrap ValueMomentumStrategy to produce a signal float."""
    def __init__(self, strategy):
        self.strategy = strategy

    def signal(self, prices: list[float]) -> float:
        sig = self.strategy.generate_signal(prices)
        return max(-1.0, min(1.0, sig.combined_score))
