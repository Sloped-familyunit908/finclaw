"""
Momentum Rotation Strategy
===========================
Cross-asset momentum rotation: buys when recent returns exceed a threshold,
sells when momentum fades. Uses lookback period for momentum calculation
and rebalances at configurable intervals.
"""

from __future__ import annotations

from typing import Any

from .base import Strategy, StrategySignal, StrategyMeta


class MomentumRotationStrategy(Strategy):
    """Momentum-based rotation strategy.

    Parameters:
        lookback: Bars for momentum calculation.
        rebalance_period: Bars between rebalance checks.
        buy_threshold: Minimum return for buy signal.
        sell_threshold: Return below which to sell.
        initial_capital: Starting capital for backtesting.
    """

    def __init__(
        self,
        lookback: int = 20,
        rebalance_period: int = 10,
        buy_threshold: float = 0.05,
        sell_threshold: float = -0.03,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.lookback = lookback
        self.rebalance_period = rebalance_period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Momentum Rotation",
            slug="momentum-rotation",
            category="universal",
            description=(
                "Cross-asset momentum rotation strategy. Calculates return over a "
                "lookback window and generates buy signals when momentum exceeds a "
                "threshold, sell signals when it drops below. Rebalances periodically."
            ),
            parameters={
                "lookback": "Bars for momentum calculation (default: 20)",
                "rebalance_period": "Bars between rebalance checks (default: 10)",
                "buy_threshold": "Min return for buy signal (default: 0.05)",
                "sell_threshold": "Return below which to sell (default: -0.03)",
            },
            usage_example=(
                'from src.strategies.library.momentum_rotation import MomentumRotationStrategy\n'
                'strategy = MomentumRotationStrategy(lookback=20, rebalance_period=10)\n'
                'signals = strategy.generate_signals(ohlcv_data)'
            ),
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate signals based on momentum over the lookback period."""
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]

        for i in range(len(data)):
            if i < self.lookback:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            # Only check on rebalance bars
            if (i - self.lookback) % self.rebalance_period != 0:
                signals.append(StrategySignal(action="hold", confidence=0.0))
                continue

            momentum = (closes[i] / closes[i - self.lookback]) - 1.0

            if momentum >= self.buy_threshold:
                confidence = min(1.0, momentum / (self.buy_threshold * 3))
                signals.append(StrategySignal(
                    action="buy", confidence=max(0.1, confidence),
                    price=closes[i],
                    reason=f"Momentum {momentum:+.2%} > {self.buy_threshold:+.2%}",
                ))
            elif momentum <= self.sell_threshold:
                confidence = min(1.0, abs(momentum) / (abs(self.sell_threshold) * 3))
                signals.append(StrategySignal(
                    action="sell", confidence=max(0.1, confidence),
                    price=closes[i],
                    reason=f"Momentum {momentum:+.2%} < {self.sell_threshold:+.2%}",
                ))
            else:
                signals.append(StrategySignal(action="hold", confidence=0.0))

        return signals
