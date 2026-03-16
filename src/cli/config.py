"""
FinClaw CLI Config Manager v5.7.0
Manages ~/.finclaw/config.yaml with dot-notation access, API key storage, and defaults.
"""

import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_CONFIG = {
    "exchanges": [],
    "default_exchange": "binance",
    "data_source": "yfinance",
    "mode": "paper",
    "default_strategy": "momentum",
    "cache_dir": "~/.finclaw/cache",
    "log_level": "info",
    "api_keys": {},
    "backtest": {
        "commission": 0.001,
        "slippage": 0.0005,
        "initial_capital": 100000,
        "period": "5y",
    },
    "strategies": {
        "momentum": {"lookback": 20, "hold_period": 5},
        "mean_reversion": {"lookback": 14, "hold_period": 3},
        "grid_trading": {"grid_size": 10, "grid_spacing": 0.02},
    },
    "risk": {
        "max_position_pct": 0.10,
        "max_drawdown_pct": 0.20,
        "stop_loss_pct": 0.05,
    },
    "display": {
        "color": True,
        "theme": "dark",
        "sparkline_width": 20,
    },
}

CONFIG_DIR = Path.home() / ".finclaw"
DEFAULT_PATH = CONFIG_DIR / "config.yaml"


class ConfigManager:
    """Manages FinClaw configuration with YAML persistence."""

    def __init__(self, path: Optional[str] = None):
        self._path = Path(path) if path else DEFAULT_PATH
        self._data: Dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def _load(self) -> None:
        """Load config from file, merging with defaults."""
        if not self._path.exists():
            return

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                if HAS_YAML:
                    raw = yaml.safe_load(f) or {}
                else:
                    import json
                    raw = json.load(f)
            self._deep_merge(self._data, raw)
        except Exception:
            pass  # Fall back to defaults

    def _deep_merge(self, base: dict, override: dict) -> None:
        """Deep merge override into base."""
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_merge(base[k], v)
            else:
                base[k] = v

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key, e.g. 'backtest.commission'."""
        parts = key.split(".")
        obj = self._data
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """Set config value by dot-notation key."""
        parts = key.split(".")
        obj = self._data
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    def get_api_key(self, exchange: str) -> Optional[str]:
        """Get API key for an exchange."""
        keys = self.get("api_keys", {})
        entry = keys.get(exchange, {})
        if isinstance(entry, dict):
            return entry.get("api_key")
        return entry if isinstance(entry, str) else None

    def set_api_key(self, exchange: str, api_key: str, secret: str = "") -> None:
        """Set API key for an exchange."""
        keys = self.get("api_keys", {})
        if not isinstance(keys, dict):
            keys = {}
        keys[exchange] = {"api_key": api_key, "secret": secret}
        self.set("api_keys", keys)

    def save(self) -> None:
        """Save config to YAML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            if HAS_YAML:
                yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)
            else:
                import json
                json.dump(self._data, f, indent=2)

    def reset(self) -> None:
        """Reset to default configuration."""
        self._data = copy.deepcopy(DEFAULT_CONFIG)

    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dict."""
        return copy.deepcopy(self._data)

    @property
    def path(self) -> Path:
        """Config file path."""
        return self._path

    def __repr__(self) -> str:
        return f"ConfigManager(path={self._path})"
