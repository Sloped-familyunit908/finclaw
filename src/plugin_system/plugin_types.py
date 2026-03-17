"""
FinClaw Strategy Plugin Types
Standard interface for all strategy plugins.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class StrategyPlugin(ABC):
    """
    Base class for all FinClaw strategy plugins.

    Community authors subclass this to create shareable strategies.
    Strategies are discovered via pip entry_points, local directories, or single files.

    Example::

        class MyStrategy(StrategyPlugin):
            name = "my_strategy"
            version = "1.0.0"
            description = "My awesome strategy"
            author = "me"
            risk_level = "medium"
            markets = ["us_stock"]

            def generate_signals(self, data: pd.DataFrame) -> pd.Series:
                sma20 = data["Close"].rolling(20).mean()
                sma50 = data["Close"].rolling(50).mean()
                signals = pd.Series(0, index=data.index)
                signals[sma20 > sma50] = 1
                signals[sma20 < sma50] = -1
                return signals

            def get_parameters(self) -> dict:
                return {"fast_period": 20, "slow_period": 50}
    """

    # -- Required metadata (set as class attributes) --
    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""
    author: str = "unknown"
    risk_level: str = "medium"  # low / medium / high
    markets: list[str] = []  # e.g. ["us_stock", "crypto", "forex", "cn_stock"]

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from OHLCV data.

        Args:
            data: DataFrame with columns like Open, High, Low, Close, Volume.
                  Index is DatetimeIndex.

        Returns:
            pd.Series with values:
              1 = buy, -1 = sell, 0 = hold
              Index should match data.index.
        """
        ...

    @abstractmethod
    def get_parameters(self) -> dict[str, Any]:
        """
        Return current strategy parameters.

        Returns:
            Dict of parameter names to current values.
        """
        ...

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Update strategy parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def backtest_config(self) -> dict[str, Any]:
        """
        Return recommended backtest configuration.

        Override to suggest default backtest settings for this strategy.
        """
        return {
            "initial_capital": 100000,
            "commission": 0.001,
            "slippage": 0.0005,
        }

    def validate(self) -> list[str]:
        """Validate plugin metadata. Returns list of issues (empty = OK)."""
        issues = []
        if self.name == "unnamed":
            issues.append("name is not set")
        if self.risk_level not in ("low", "medium", "high"):
            issues.append(f"invalid risk_level: {self.risk_level}")
        if not self.markets:
            issues.append("markets list is empty")
        return issues

    def get_info(self) -> dict[str, str]:
        """Return plugin metadata as dict."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "risk_level": self.risk_level,
            "markets": self.markets,
        }

    def __repr__(self) -> str:
        return f"<StrategyPlugin {self.name} v{self.version}>"
