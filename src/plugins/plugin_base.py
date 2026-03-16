"""
FinClaw Plugin Base Classes
Abstract base for all plugin types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    """Base class for all FinClaw plugins."""

    name: str = "unnamed"
    version: str = "0.1.0"
    description: str = ""
    plugin_type: str = "generic"

    def on_load(self, context: dict[str, Any] | None = None) -> None:
        """Called when the plugin is loaded. Override for setup."""
        pass

    def on_unload(self) -> None:
        """Called when the plugin is unloaded. Override for cleanup."""
        pass

    def get_info(self) -> dict[str, str]:
        """Return plugin metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "type": self.plugin_type,
        }
