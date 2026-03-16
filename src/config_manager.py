"""
FinClaw Configuration Manager v2.6.0
Enhanced configuration system with YAML support, validation, and defaults.
"""

import os
from typing import Any, Dict, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


DEFAULT_CONFIG = {
    "default": {
        "data_source": "yfinance",
        "cache_dir": "~/.finclaw/cache",
        "log_level": "info",
    },
    "backtest": {
        "commission": 0.001,
        "slippage": 0.0005,
        "initial_capital": 100000,
        "period": "5y",
    },
    "strategies": {
        "momentum": {"lookback": 20, "hold_period": 5},
        "mean_reversion": {"lookback": 14, "hold_period": 3},
        "trend_following": {"fast_ma": 10, "slow_ma": 50},
    },
    "risk": {
        "max_position_pct": 0.10,
        "max_drawdown_pct": 0.20,
        "stop_loss_pct": 0.05,
    },
    "report": {
        "output_dir": "reports",
        "format": "html",
        "theme": "dark",
    },
}

VALIDATION_RULES = {
    "backtest.commission": (float, 0.0, 1.0),
    "backtest.slippage": (float, 0.0, 1.0),
    "backtest.initial_capital": (float, 1.0, 1e12),
    "risk.max_position_pct": (float, 0.0, 1.0),
    "risk.max_drawdown_pct": (float, 0.0, 1.0),
    "risk.stop_loss_pct": (float, 0.0, 1.0),
}


class ConfigValidationError(Exception):
    """Invalid configuration."""
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__("Config errors:\n" + "\n".join(f"  - {e}" for e in errors))


class ConfigManager:
    """Enhanced configuration manager with nested access and validation."""

    def __init__(self, data: Dict[str, Any] = None):
        import copy
        self._data = data or copy.deepcopy(DEFAULT_CONFIG)

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

    def get_strategy_config(self, name: str) -> Dict[str, Any]:
        """Get strategy-specific config."""
        return self.get(f"strategies.{name}", {})

    def validate(self) -> None:
        """Validate configuration. Raises ConfigValidationError on failure."""
        errors = []
        for key, (typ, lo, hi) in VALIDATION_RULES.items():
            val = self.get(key)
            if val is not None:
                try:
                    val = typ(val)
                except (TypeError, ValueError):
                    errors.append(f"{key}: expected {typ.__name__}, got {type(val).__name__}")
                    continue
                if not (lo <= val <= hi):
                    errors.append(f"{key}: {val} not in [{lo}, {hi}]")
        if errors:
            raise ConfigValidationError(errors)

    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dict."""
        return dict(self._data)

    def save(self, path: str = None) -> None:
        """Save config to YAML file."""
        path = path or os.path.expanduser("~/.finclaw/config.yml")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if HAS_YAML:
            with open(path, "w") as f:
                yaml.dump(self._data, f, default_flow_style=False)
        else:
            import json
            with open(path, "w") as f:
                json.dump(self._data, f, indent=2)

    @classmethod
    def load(cls, path: str = None) -> "ConfigManager":
        """Load config from YAML, falling back to defaults."""
        candidates = [
            path,
            os.path.join(os.getcwd(), "finclaw.yml"),
            os.path.expanduser("~/.finclaw/config.yml"),
            os.path.expanduser("~/.finclaw.yml"),
        ]

        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return cls._from_file(candidate)

        return cls()

    @classmethod
    def _from_file(cls, path: str) -> "ConfigManager":
        """Load from a specific file, merging with defaults."""
        data = dict(DEFAULT_CONFIG)

        if HAS_YAML:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}
            except Exception:
                return cls(data)
        else:
            import json
            try:
                with open(path, "r") as f:
                    raw = json.load(f)
            except Exception:
                return cls(data)

        # Deep merge
        _deep_merge(data, raw)
        config = cls(data)
        config.validate()
        return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
