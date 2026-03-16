"""
Funding Rate Arbitrage
======================
Long spot + short perpetual futures to capture funding rate payments.

Parameters:
    entry_threshold: Min funding rate (annualized %) to enter (default: 10).
    exit_threshold: Funding rate below this to exit (default: 2).
    initial_capital: Starting capital (default: 10000).

Usage:
    strategy = FundingRateArbitrage(entry_threshold=15, exit_threshold=3)
    signals = strategy.generate_signals(data_with_funding_rate)
    result = strategy.backtest(data_with_funding_rate)

Data format:
    Each bar dict must include 'close' and 'funding_rate' (8h rate as decimal, e.g., 0.01 = 1%).
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta


class FundingRateArbitrage(Strategy):
    """Capture funding rate by going long spot / short perp when rate is high."""

    def __init__(
        self,
        entry_threshold: float = 10.0,
        exit_threshold: float = 2.0,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Funding Rate Arbitrage",
            slug="funding-rate",
            category="crypto",
            description="Long spot + short perp to capture funding rate. Market-neutral strategy.",
            parameters={
                "entry_threshold": "Min annualized funding rate (%) to enter (default: 10)",
                "exit_threshold": "Exit when funding rate drops below this (default: 2)",
            },
            usage_example="finclaw strategy backtest funding-rate --symbol BTCUSDT --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        in_position = False

        for bar in data:
            price = bar["close"]
            # funding_rate is 8h rate as decimal; annualize: rate * 3 * 365 * 100
            fr = bar.get("funding_rate", 0.0)
            annualized = fr * 3 * 365 * 100

            if not in_position and annualized >= self.entry_threshold:
                signals.append(StrategySignal(
                    "buy", min(annualized / 50, 1.0), price=price,
                    reason=f"funding rate {annualized:.1f}% > {self.entry_threshold}%",
                    metadata={"funding_rate_annualized": annualized},
                ))
                in_position = True
            elif in_position and annualized < self.exit_threshold:
                signals.append(StrategySignal(
                    "sell", 0.7, price=price,
                    reason=f"funding rate {annualized:.1f}% < {self.exit_threshold}%",
                    metadata={"funding_rate_annualized": annualized},
                ))
                in_position = False
            else:
                signals.append(StrategySignal(
                    "hold", 0.0, price=price,
                    reason="funding rate in range" if in_position else "waiting for entry",
                    metadata={"funding_rate_annualized": annualized},
                ))

        return signals
