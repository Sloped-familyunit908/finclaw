"""
FinClaw Plugin System
Load and manage plugins that extend FinClaw with custom strategies,
data sources, indicators, and exporters.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

PLUGIN_TYPES = {"strategy", "data_source", "indicator", "exporter"}


@dataclass
class PluginInfo:
    """Metadata about a loaded plugin."""
    name: str
    path: str
    plugin_type: str
    version: str = "0.0.0"
    description: str = ""
    active: bool = True
    instance: Any = None


class PluginManager:
    """
    Discover, load, and manage FinClaw plugins.

    A plugin is a Python module with a `register(manager)` function.
    The register function should call manager.add_strategy / add_indicator etc.

    Usage:
        pm = PluginManager()
        pm.load_plugin("plugins/my_strategy.py")
        pm.list_plugins()
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._strategies: dict[str, Any] = {}
        self._indicators: dict[str, Callable] = {}
        self._data_sources: dict[str, Any] = {}
        self._exporters: dict[str, Any] = {}

    def load_plugin(self, path: str) -> PluginInfo:
        """Load a plugin from a Python file path."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Plugin not found: {path}")

        name = os.path.splitext(os.path.basename(path))[0]
        if name in self._plugins:
            raise ValueError(f"Plugin already loaded: {name}")

        spec = importlib.util.spec_from_file_location(f"finclaw_plugin_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        info = PluginInfo(
            name=name,
            path=path,
            plugin_type=getattr(module, "PLUGIN_TYPE", "strategy"),
            version=getattr(module, "__version__", "0.0.0"),
            description=getattr(module, "__description__", ""),
            instance=module,
        )

        # Call register hook if present
        if hasattr(module, "register"):
            module.register(self)

        self._plugins[name] = info
        logger.info("Loaded plugin: %s (%s) from %s", name, info.plugin_type, path)
        return info

    def load_directory(self, directory: str) -> list[PluginInfo]:
        """Load all .py plugins from a directory."""
        loaded = []
        if not os.path.isdir(directory):
            return loaded
        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    info = self.load_plugin(os.path.join(directory, filename))
                    loaded.append(info)
                except Exception as exc:
                    logger.warning("Failed to load plugin %s: %s", filename, exc)
        return loaded

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin by name."""
        if name not in self._plugins:
            return False
        info = self._plugins.pop(name)
        # Clean up registered items
        self._strategies.pop(name, None)
        self._indicators.pop(name, None)
        self._data_sources.pop(name, None)
        self._exporters.pop(name, None)
        logger.info("Unloaded plugin: %s", name)
        return True

    def list_plugins(self) -> list[PluginInfo]:
        """List all loaded plugins."""
        return list(self._plugins.values())

    def get_plugin(self, name: str) -> PluginInfo | None:
        return self._plugins.get(name)

    # --- Registration hooks (called by plugins) ---

    def add_strategy(self, name: str, strategy: Any) -> None:
        self._strategies[name] = strategy
        logger.debug("Registered strategy: %s", name)

    def add_indicator(self, name: str, func: Callable) -> None:
        self._indicators[name] = func
        logger.debug("Registered indicator: %s", name)

    def add_data_source(self, name: str, source: Any) -> None:
        self._data_sources[name] = source
        logger.debug("Registered data source: %s", name)

    def add_exporter(self, name: str, exporter: Any) -> None:
        self._exporters[name] = exporter
        logger.debug("Registered exporter: %s", name)

    # --- Accessors ---

    @property
    def strategies(self) -> dict[str, Any]:
        return dict(self._strategies)

    @property
    def indicators(self) -> dict[str, Callable]:
        return dict(self._indicators)

    @property
    def data_sources(self) -> dict[str, Any]:
        return dict(self._data_sources)

    @property
    def exporters(self) -> dict[str, Any]:
        return dict(self._exporters)
