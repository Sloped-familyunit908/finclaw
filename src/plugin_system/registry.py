"""
FinClaw Strategy Registry
Unified management of built-in + plugin strategies.
Supports filtering by market/risk_level and multi-strategy voting.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin
from src.plugin_system.plugin_loader import PluginLoader

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Central registry for all strategy plugins.

    Usage::

        registry = StrategyRegistry()
        registry.load_all()

        # List strategies
        for s in registry.list():
            print(s.name, s.risk_level)

        # Filter
        crypto = registry.filter(market="crypto")
        safe = registry.filter(risk_level="low")

        # Multi-strategy voting
        combined = registry.vote(["trend_following", "mean_reversion"], data)
    """

    def __init__(self) -> None:
        self._loader = PluginLoader()
        self._strategies: dict[str, StrategyPlugin] = {}

    def load_all(self) -> list[StrategyPlugin]:
        """Load all strategies from all sources."""
        plugins = self._loader.discover_all()
        for p in plugins:
            self._strategies[p.name] = p
        return plugins

    def register(self, plugin: StrategyPlugin) -> None:
        """Manually register a strategy plugin."""
        self._strategies[plugin.name] = plugin
        self._loader._loaded[plugin.name] = plugin

    def unregister(self, name: str) -> bool:
        """Remove a strategy from the registry."""
        removed = self._strategies.pop(name, None) is not None
        self._loader.unload(name)
        return removed

    def get(self, name: str) -> StrategyPlugin | None:
        """Get a strategy by name."""
        return self._strategies.get(name)

    def list(self) -> list[StrategyPlugin]:
        """List all registered strategies."""
        return list(self._strategies.values())

    def names(self) -> list[str]:
        """List all strategy names."""
        return list(self._strategies.keys())

    def filter(
        self,
        market: str | None = None,
        risk_level: str | None = None,
    ) -> list[StrategyPlugin]:
        """Filter strategies by market and/or risk level."""
        result = self.list()
        if market:
            result = [s for s in result if market in s.markets]
        if risk_level:
            result = [s for s in result if s.risk_level == risk_level]
        return result

    def vote(
        self,
        strategy_names: list[str],
        data: pd.DataFrame,
        threshold: float = 0.5,
    ) -> pd.Series:
        """
        Run multiple strategies and combine signals via majority voting.

        Args:
            strategy_names: Names of strategies to run.
            data: OHLCV DataFrame.
            threshold: Fraction of strategies that must agree (0-1).

        Returns:
            pd.Series with combined signals (1=buy, -1=sell, 0=hold).
        """
        if not strategy_names:
            return pd.Series(0, index=data.index)

        all_signals: list[pd.Series] = []
        for name in strategy_names:
            strat = self.get(name)
            if strat is None:
                logger.warning("Strategy not found for voting: %s", name)
                continue
            try:
                signals = strat.generate_signals(data)
                all_signals.append(signals)
            except Exception as exc:
                logger.warning("Strategy %s failed: %s", name, exc)

        if not all_signals:
            return pd.Series(0, index=data.index)

        # Majority voting
        combined = pd.Series(0, index=data.index)
        min_votes = max(1, int(len(all_signals) * threshold))

        for i in range(len(data)):
            votes = Counter()
            for sig in all_signals:
                val = sig.iloc[i] if i < len(sig) else 0
                if val == 1:
                    votes["buy"] += 1
                elif val == -1:
                    votes["sell"] += 1

            if votes.get("buy", 0) >= min_votes:
                combined.iloc[i] = 1
            elif votes.get("sell", 0) >= min_votes:
                combined.iloc[i] = -1

        return combined

    def load_directory(self, directory: str) -> list[StrategyPlugin]:
        """Load plugins from a local directory and register them."""
        plugins = self._loader.load_directory(directory)
        for p in plugins:
            self._strategies[p.name] = p
        return plugins

    def load_file(self, path: str) -> list[StrategyPlugin]:
        """Load plugins from a single file and register them."""
        plugins = self._loader.load_file(path)
        for p in plugins:
            self._strategies[p.name] = p
        return plugins
