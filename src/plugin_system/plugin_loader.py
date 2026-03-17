"""
FinClaw Strategy Plugin Loader
Discover and load strategy plugins from three sources:
1. pip-installed packages (entry_points group: finclaw.strategies)
2. Local plugin directories
3. Single Python files
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import os
import sys
from typing import Any

from src.plugin_system.plugin_types import StrategyPlugin

logger = logging.getLogger(__name__)

# Entry point group name for pip-installed strategy plugins
ENTRY_POINT_GROUP = "finclaw.strategies"


class PluginLoader:
    """
    Discovers and loads StrategyPlugin implementations.

    Usage::

        loader = PluginLoader()
        plugins = loader.discover_all()
        for p in plugins:
            print(p.name, p.version)
    """

    def __init__(self) -> None:
        self._loaded: dict[str, StrategyPlugin] = {}

    @property
    def loaded(self) -> dict[str, StrategyPlugin]:
        """All currently loaded plugins by name."""
        return dict(self._loaded)

    # -- Discovery methods --

    def discover_all(self) -> list[StrategyPlugin]:
        """Discover plugins from all sources: entry_points, built-in, local dirs."""
        plugins: list[StrategyPlugin] = []
        plugins.extend(self.discover_entry_points())
        plugins.extend(self.discover_builtin())
        return plugins

    def discover_entry_points(self) -> list[StrategyPlugin]:
        """Discover pip-installed finclaw-strategy-* packages via entry_points."""
        plugins: list[StrategyPlugin] = []

        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
            eps = entry_points(group=ENTRY_POINT_GROUP)
        else:
            # Python 3.9 compat
            from importlib.metadata import entry_points as _ep
            all_eps = _ep()
            eps = all_eps.get(ENTRY_POINT_GROUP, [])

        for ep in eps:
            try:
                plugin_cls = ep.load()
                if inspect.isclass(plugin_cls) and issubclass(plugin_cls, StrategyPlugin):
                    instance = plugin_cls()
                    if instance.name not in self._loaded:
                        self._loaded[instance.name] = instance
                        plugins.append(instance)
                        logger.info("Loaded entry_point plugin: %s v%s", instance.name, instance.version)
                elif isinstance(plugin_cls, StrategyPlugin):
                    # Already an instance
                    if plugin_cls.name not in self._loaded:
                        self._loaded[plugin_cls.name] = plugin_cls
                        plugins.append(plugin_cls)
                else:
                    logger.warning("Entry point %s is not a StrategyPlugin", ep.name)
            except Exception as exc:
                logger.warning("Failed to load entry_point %s: %s", ep.name, exc)

        return plugins

    def discover_builtin(self) -> list[StrategyPlugin]:
        """Load built-in strategies wrapped as plugins."""
        plugins: list[StrategyPlugin] = []
        try:
            from src.plugin_system.builtin_adapters import get_builtin_plugins
            for p in get_builtin_plugins():
                if p.name not in self._loaded:
                    self._loaded[p.name] = p
                    plugins.append(p)
        except Exception as exc:
            logger.warning("Failed to load built-in plugins: %s", exc)
        return plugins

    def load_directory(self, directory: str) -> list[StrategyPlugin]:
        """Load all strategy plugins from a local directory."""
        plugins: list[StrategyPlugin] = []
        if not os.path.isdir(directory):
            return plugins

        for filename in sorted(os.listdir(directory)):
            if filename.endswith(".py") and not filename.startswith("_"):
                path = os.path.join(directory, filename)
                try:
                    loaded = self.load_file(path)
                    if loaded:
                        plugins.extend(loaded)
                except Exception as exc:
                    logger.warning("Failed to load %s: %s", filename, exc)

        return plugins

    def load_file(self, path: str) -> list[StrategyPlugin]:
        """Load strategy plugin(s) from a single Python file."""
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Plugin file not found: {path}")

        name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(f"finclaw_strategy_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugins: list[StrategyPlugin] = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (inspect.isclass(attr)
                    and issubclass(attr, StrategyPlugin)
                    and attr is not StrategyPlugin
                    and not inspect.isabstract(attr)):
                instance = attr()
                if instance.name not in self._loaded:
                    self._loaded[instance.name] = instance
                    plugins.append(instance)
                    logger.info("Loaded file plugin: %s from %s", instance.name, path)

        return plugins

    def get(self, name: str) -> StrategyPlugin | None:
        """Get a loaded plugin by name."""
        return self._loaded.get(name)

    def unload(self, name: str) -> bool:
        """Unload a plugin by name."""
        return self._loaded.pop(name, None) is not None
