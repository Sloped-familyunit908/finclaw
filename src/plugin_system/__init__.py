"""
FinClaw Strategy Plugin System
===============================
Ecosystem for community-contributed trading strategies.

Three loading methods:
1. pip packages (entry_points: finclaw.strategies)
2. Local directory scanning
3. Single file loading

Ecosystem adapters:
- BacktraderAdapter: Wrap bt.Strategy classes
- TALibSignalGenerator: Use TA-Lib indicators as strategies
- PineScriptPlugin: Parse TradingView Pine Script
"""

from src.plugin_system.plugin_types import StrategyPlugin
from src.plugin_system.plugin_loader import PluginLoader
from src.plugin_system.registry import StrategyRegistry

__all__ = [
    "StrategyPlugin",
    "PluginLoader",
    "StrategyRegistry",
]
