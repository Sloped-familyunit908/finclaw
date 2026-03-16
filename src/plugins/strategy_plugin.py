"""
FinClaw Strategy Plugin Interface
Allows users to write custom trading strategies as plugins.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from src.plugins.plugin_base import Plugin


class StrategyPlugin(Plugin):
    """
    Base class for strategy plugins.

    Subclass this and implement generate_signals() and get_parameters().
    Optionally override optimize() for parameter optimization.
    """

    plugin_type: str = "strategy"

    @abstractmethod
    def generate_signals(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate trading signals from market data.

        Args:
            data: Dict with keys like 'ohlcv' (list of candles), 'symbol', 'timeframe'.

        Returns:
            List of signal dicts with keys: timestamp, action ('buy'/'sell'/'hold'),
            symbol, confidence (0-1), reason (str).
        """
        ...

    @abstractmethod
    def get_parameters(self) -> dict[str, Any]:
        """
        Return current strategy parameters.

        Returns:
            Dict of parameter names to values, e.g. {'window': 20, 'threshold': 0.02}.
        """
        ...

    def set_parameters(self, params: dict[str, Any]) -> None:
        """Update strategy parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def optimize(self, data: dict[str, Any], metric: str = "sharpe") -> dict[str, Any]:
        """
        Optimize strategy parameters on historical data.

        Args:
            data: Historical market data.
            metric: Optimization target ('sharpe', 'returns', 'sortino', 'max_drawdown').

        Returns:
            Dict of optimized parameters.
        """
        # Default: return current params (subclasses can override)
        return self.get_parameters()

    def backtest(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Run a simple backtest using generate_signals.

        Returns:
            Dict with keys: signals_count, buy_count, sell_count.
        """
        signals = self.generate_signals(data)
        buys = [s for s in signals if s.get("action") == "buy"]
        sells = [s for s in signals if s.get("action") == "sell"]
        return {
            "signals_count": len(signals),
            "buy_count": len(buys),
            "sell_count": len(sells),
        }
