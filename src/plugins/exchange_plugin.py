"""
FinClaw Exchange Plugin Interface
Third-party exchange adapters as plugins.
"""

from __future__ import annotations

from typing import Any

from src.plugins.plugin_base import Plugin
from src.exchanges.base import ExchangeAdapter


class ExchangePlugin(Plugin, ExchangeAdapter):
    """
    Base class for exchange plugins.

    Combines Plugin lifecycle with ExchangeAdapter interface.
    Users can add new exchanges without modifying core code.

    Subclass this and implement all ExchangeAdapter abstract methods
    plus the Plugin lifecycle hooks.
    """

    plugin_type: str = "exchange"
    exchange_type: str = "custom"

    def __init__(self, config: dict[str, Any] | None = None):
        Plugin.__init__(self)
        ExchangeAdapter.__init__(self, config)

    def on_load(self, context: dict[str, Any] | None = None) -> None:
        """Register this exchange with the ExchangeRegistry on load."""
        from src.exchanges.registry import ExchangeRegistry
        ExchangeRegistry.register(self.name, type(self), self.exchange_type)

    def on_unload(self) -> None:
        """Unregister from the ExchangeRegistry on unload."""
        from src.exchanges.registry import ExchangeRegistry
        if self.name.lower() in ExchangeRegistry._exchanges:
            del ExchangeRegistry._exchanges[self.name.lower()]
            ExchangeRegistry._type_map.pop(self.name.lower(), None)
