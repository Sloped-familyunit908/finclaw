"""Plugin system for extending FinClaw."""

from .plugin_base import Plugin
from .plugin_manager import PluginManager, PluginInfo
from .strategy_plugin import StrategyPlugin
from .indicator_plugin import IndicatorPlugin
from .exchange_plugin import ExchangePlugin

__all__ = [
    "Plugin",
    "PluginManager",
    "PluginInfo",
    "StrategyPlugin",
    "IndicatorPlugin",
    "ExchangePlugin",
]
