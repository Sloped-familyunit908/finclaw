"""
FinClaw Plugin Manager
Discover, load, manage, and create plugins with ABC-based plugin system.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.plugins.plugin_base import Plugin

logger = logging.getLogger(__name__)

DEFAULT_PLUGIN_DIR = os.path.join(os.path.expanduser("~"), ".finclaw", "plugins")

PLUGIN_TYPES = {"strategy", "indicator", "exchange", "exporter", "data_source", "generic"}


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

    Supports both:
    - Legacy module-based plugins (with register() function)
    - New ABC-based plugins (subclassing Plugin)
    """

    def __init__(self, plugin_dir: str | None = None) -> None:
        self.plugin_dir = plugin_dir or DEFAULT_PLUGIN_DIR
        self._plugins: dict[str, PluginInfo] = {}
        self._strategies: dict[str, Any] = {}
        self._indicators: dict[str, Callable] = {}
        self._data_sources: dict[str, Any] = {}
        self._exporters: dict[str, Any] = {}
        self._exchanges: dict[str, Any] = {}
        self._context: dict[str, Any] = {}

    def set_context(self, context: dict[str, Any]) -> None:
        """Set context passed to plugins on load."""
        self._context = context

    def discover(self) -> list[str]:
        """Scan plugin_dir for available plugins (not yet loaded)."""
        available = []
        if not os.path.isdir(self.plugin_dir):
            return available
        for filename in sorted(os.listdir(self.plugin_dir)):
            if filename.endswith(".py") and not filename.startswith("_"):
                name = os.path.splitext(filename)[0]
                available.append(name)
        return available

    def load(self, name: str) -> PluginInfo:
        """Load a plugin by name from plugin_dir, or by full path."""
        if name in self._plugins:
            raise ValueError(f"Plugin already loaded: {name}")

        # Resolve path
        if os.path.isfile(name):
            path = name
            name = os.path.splitext(os.path.basename(name))[0]
        else:
            path = os.path.join(self.plugin_dir, f"{name}.py")

        if not os.path.isfile(path):
            raise FileNotFoundError(f"Plugin not found: {path}")

        return self._load_from_path(name, path)

    def _load_from_path(self, name: str, path: str) -> PluginInfo:
        """Load a plugin from a file path."""
        spec = importlib.util.spec_from_file_location(f"finclaw_plugin_{name}", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Plugin subclass in module
        plugin_instance = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (inspect.isclass(attr) and issubclass(attr, Plugin)
                    and attr is not Plugin and not inspect.isabstract(attr)):
                plugin_instance = attr()
                break

        if plugin_instance:
            # ABC-based plugin
            plugin_instance.on_load(self._context)
            info = PluginInfo(
                name=plugin_instance.name,
                path=path,
                plugin_type=plugin_instance.plugin_type,
                version=plugin_instance.version,
                description=plugin_instance.description,
                instance=plugin_instance,
            )
            self._register_plugin_by_type(info)
        else:
            # Legacy module-based plugin
            info = PluginInfo(
                name=name,
                path=path,
                plugin_type=getattr(module, "PLUGIN_TYPE", "strategy"),
                version=getattr(module, "__version__", "0.0.0"),
                description=getattr(module, "__description__", ""),
                instance=module,
            )
            if hasattr(module, "register"):
                module.register(self)

        if info.name in self._plugins:
            raise ValueError(f"Plugin already loaded: {info.name}")
        self._plugins[info.name] = info
        logger.info("Loaded plugin: %s (%s) v%s", info.name, info.plugin_type, info.version)
        return info

    def _register_plugin_by_type(self, info: PluginInfo) -> None:
        """Auto-register plugin instance in the appropriate registry."""
        from src.plugins.strategy_plugin import StrategyPlugin
        from src.plugins.indicator_plugin import IndicatorPlugin
        from src.plugins.exchange_plugin import ExchangePlugin

        inst = info.instance
        if isinstance(inst, StrategyPlugin):
            self._strategies[info.name] = inst
        elif isinstance(inst, IndicatorPlugin):
            self._indicators[info.name] = inst
        elif isinstance(inst, ExchangePlugin):
            self._exchanges[info.name] = inst

    def unload(self, name: str) -> bool:
        """Unload a plugin by name."""
        if name not in self._plugins:
            return False
        info = self._plugins.pop(name)
        if isinstance(info.instance, Plugin):
            info.instance.on_unload()
        self._strategies.pop(name, None)
        self._indicators.pop(name, None)
        self._exchanges.pop(name, None)
        self._data_sources.pop(name, None)
        self._exporters.pop(name, None)
        logger.info("Unloaded plugin: %s", name)
        return True

    def load_all(self) -> list[PluginInfo]:
        """Load all discovered plugins."""
        loaded = []
        for name in self.discover():
            if name not in self._plugins:
                try:
                    loaded.append(self.load(name))
                except Exception as exc:
                    logger.warning("Failed to load plugin %s: %s", name, exc)
        return loaded

    def list_plugins(self) -> list[PluginInfo]:
        """List all loaded plugins."""
        return list(self._plugins.values())

    def get_plugin(self, name: str) -> PluginInfo | None:
        return self._plugins.get(name)

    def install(self, source: str) -> PluginInfo:
        """Install a plugin from a file path into plugin_dir."""
        if not os.path.isfile(source):
            raise FileNotFoundError(f"Source not found: {source}")
        os.makedirs(self.plugin_dir, exist_ok=True)
        dest = os.path.join(self.plugin_dir, os.path.basename(source))
        shutil.copy2(source, dest)
        return self.load(os.path.splitext(os.path.basename(source))[0])

    def create(self, name: str, plugin_type: str = "strategy") -> str:
        """
        Create a new plugin from template.

        Returns:
            Path to the created plugin file.
        """
        os.makedirs(self.plugin_dir, exist_ok=True)
        path = os.path.join(self.plugin_dir, f"{name}.py")
        if os.path.exists(path):
            raise FileExistsError(f"Plugin already exists: {path}")

        templates = {
            "strategy": _STRATEGY_TEMPLATE,
            "indicator": _INDICATOR_TEMPLATE,
            "exchange": _EXCHANGE_TEMPLATE,
        }
        template = templates.get(plugin_type, _STRATEGY_TEMPLATE)
        content = template.replace("{{NAME}}", name).replace(
            "{{CLASS_NAME}}", name.replace("_", " ").title().replace(" ", "")
        )

        with open(path, "w") as f:
            f.write(content)
        logger.info("Created %s plugin: %s", plugin_type, path)
        return path

    # --- Legacy registration hooks (called by old-style plugins) ---

    def add_strategy(self, name: str, strategy: Any) -> None:
        self._strategies[name] = strategy

    def add_indicator(self, name: str, func: Callable) -> None:
        self._indicators[name] = func

    def add_data_source(self, name: str, source: Any) -> None:
        self._data_sources[name] = source

    def add_exporter(self, name: str, exporter: Any) -> None:
        self._exporters[name] = exporter

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

    @property
    def exchanges(self) -> dict[str, Any]:
        return dict(self._exchanges)


# --- Plugin Templates ---

_STRATEGY_TEMPLATE = '''"""
{{CLASS_NAME}} Strategy Plugin for FinClaw
"""

from src.plugins.strategy_plugin import StrategyPlugin


class {{CLASS_NAME}}Strategy(StrategyPlugin):
    name = "{{NAME}}"
    version = "0.1.0"
    description = "Custom strategy: {{NAME}}"

    def __init__(self):
        self.window = 20
        self.threshold = 0.02

    def generate_signals(self, data: dict) -> list:
        signals = []
        ohlcv = data.get("ohlcv", [])
        # TODO: Implement your signal logic
        return signals

    def get_parameters(self) -> dict:
        return {"window": self.window, "threshold": self.threshold}
'''

_INDICATOR_TEMPLATE = '''"""
{{CLASS_NAME}} Indicator Plugin for FinClaw
"""

from src.plugins.indicator_plugin import IndicatorPlugin


class {{CLASS_NAME}}Indicator(IndicatorPlugin):
    name = "{{NAME}}"
    version = "0.1.0"
    description = "Custom indicator: {{NAME}}"

    def calculate(self, data: list, **params) -> list:
        validated = self.validate_params(**params)
        # TODO: Implement your indicator logic
        return []

    def get_params_schema(self) -> dict:
        return {
            "period": {"type": "int", "default": 14, "min": 1, "max": 200, "description": "Lookback period"},
        }
'''

_EXCHANGE_TEMPLATE = '''"""
{{CLASS_NAME}} Exchange Plugin for FinClaw
"""

from src.plugins.exchange_plugin import ExchangePlugin


class {{CLASS_NAME}}Exchange(ExchangePlugin):
    name = "{{NAME}}"
    version = "0.1.0"
    description = "Custom exchange adapter: {{NAME}}"
    exchange_type = "custom"

    def get_ohlcv(self, symbol, timeframe="1d", limit=100):
        raise NotImplementedError

    def get_ticker(self, symbol):
        raise NotImplementedError

    def get_orderbook(self, symbol, depth=20):
        raise NotImplementedError

    def place_order(self, symbol, side, type, amount, price=None):
        raise NotImplementedError

    def cancel_order(self, order_id):
        raise NotImplementedError

    def get_balance(self):
        raise NotImplementedError

    def get_positions(self):
        raise NotImplementedError
'''
