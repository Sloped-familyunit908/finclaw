"""
Pairs Trading — Statistical Arbitrage
======================================
Cointegration-based pair selection with z-score entry/exit.

Parameters:
    entry_z: Z-score threshold to enter (default: 2.0).
    exit_z: Z-score threshold to close (default: 0.5).
    stop_z: Stop-loss z-score (default: 3.5).
    lookback: Window for spread calculation (default: 60).

Usage:
    strategy = PairsTradingStrategy(entry_z=2.0, exit_z=0.5)
    signals = strategy.generate_signals(pair_data)

Data format:
    Each bar must include 'close_a' and 'close_b' for the two assets.
"""

from __future__ import annotations
import math
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


class PairsTradingStrategy(Strategy):
    """Statistical arbitrage pairs trading using spread z-score."""

    def __init__(
        self,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        stop_z: float = 3.5,
        lookback: int = 60,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.stop_z = stop_z
        self.lookback = lookback

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Pairs Trading",
            slug="pairs-trading",
            category="stock",
            description="Statistical arbitrage using cointegration and spread z-score.",
            parameters={
                "entry_z": "Z-score to enter trade (default: 2.0)",
                "exit_z": "Z-score to exit/close (default: 0.5)",
                "stop_z": "Stop-loss z-score (default: 3.5)",
                "lookback": "Window for spread stats (default: 60)",
            },
            usage_example="finclaw strategy backtest pairs-trading --symbol COCA/PEP --start 2024-01-01",
        )

    def _calc_z_score(self, spreads: list[float]) -> float:
        if len(spreads) < 2:
            return 0.0
        mean = sum(spreads) / len(spreads)
        var = sum((s - mean) ** 2 for s in spreads) / len(spreads)
        std = math.sqrt(var) if var > 0 else 1e-10
        return (spreads[-1] - mean) / std

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        position = "flat"  # flat, long_a_short_b, short_a_long_b

        for i, bar in enumerate(data):
            price_a = bar.get("close_a", bar.get("close", 0))
            price_b = bar.get("close_b", 0)

            if i < self.lookback:
                signals.append(StrategySignal("hold", 0.0, reason="warming up"))
                continue

            spreads = [d.get("close_a", d.get("close", 0)) - d.get("close_b", 0)
                       for d in data[i - self.lookback + 1: i + 1]]
            z = self._calc_z_score(spreads)

            if position == "flat":
                if z > self.entry_z:
                    signals.append(StrategySignal(
                        "sell", min(abs(z) / 4, 1.0),
                        reason=f"z={z:.2f} > {self.entry_z}: short A, long B",
                        metadata={"z_score": z, "position": "short_a_long_b"},
                    ))
                    position = "short_a_long_b"
                elif z < -self.entry_z:
                    signals.append(StrategySignal(
                        "buy", min(abs(z) / 4, 1.0),
                        reason=f"z={z:.2f} < -{self.entry_z}: long A, short B",
                        metadata={"z_score": z, "position": "long_a_short_b"},
                    ))
                    position = "long_a_short_b"
                else:
                    signals.append(StrategySignal("hold", 0.0, reason=f"z={z:.2f}, no signal"))
            else:
                if abs(z) < self.exit_z:
                    signals.append(StrategySignal(
                        "sell" if position == "long_a_short_b" else "buy",
                        0.7, reason=f"z={z:.2f} < {self.exit_z}: close position",
                        metadata={"z_score": z},
                    ))
                    position = "flat"
                elif abs(z) > self.stop_z:
                    signals.append(StrategySignal(
                        "sell" if position == "long_a_short_b" else "buy",
                        0.9, reason=f"z={z:.2f} > {self.stop_z}: stop loss",
                        metadata={"z_score": z},
                    ))
                    position = "flat"
                else:
                    signals.append(StrategySignal("hold", 0.0, reason=f"z={z:.2f}, holding"))

        return signals
