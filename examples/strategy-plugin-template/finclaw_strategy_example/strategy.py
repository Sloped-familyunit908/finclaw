"""
Golden Cross Strategy Plugin for FinClaw
=========================================
Classic 50/200 SMA crossover strategy.

Buy when 50-day SMA crosses above 200-day SMA (golden cross).
Sell when 50-day SMA crosses below 200-day SMA (death cross).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin


class GoldenCrossStrategy(StrategyPlugin):
    """
    Golden Cross / Death Cross strategy.

    A simple, well-known trend-following strategy that uses two
    simple moving averages to generate buy/sell signals.
    """

    name = "golden_cross"
    version = "1.0.0"
    description = "50/200 SMA Golden Cross / Death Cross strategy"
    author = "FinClaw Community"
    risk_level = "low"
    markets = ["us_stock", "crypto", "forex", "cn_stock"]

    def __init__(self, fast_period: int = 50, slow_period: int = 200):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate signals based on SMA crossover."""
        close = data["Close"]
        fast_sma = close.rolling(self.fast_period).mean()
        slow_sma = close.rolling(self.slow_period).mean()

        signals = pd.Series(0, index=data.index)

        # Crossover detection
        prev_fast = fast_sma.shift(1)
        prev_slow = slow_sma.shift(1)

        # Golden cross: fast crosses above slow
        golden = (prev_fast <= prev_slow) & (fast_sma > slow_sma)
        # Death cross: fast crosses below slow
        death = (prev_fast >= prev_slow) & (fast_sma < slow_sma)

        signals[golden] = 1
        signals[death] = -1

        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
        }

    def backtest_config(self) -> dict[str, Any]:
        return {
            "initial_capital": 100000,
            "commission": 0.001,
            "slippage": 0.0005,
            "lookback_days": 1000,  # Need enough data for 200-day SMA
        }
