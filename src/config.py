"""
FinClaw Configuration
Load settings from finclaw.yml with sensible defaults and validation.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigValidationError(Exception):
    """Raised when finclaw.yml contains invalid configuration."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        msg = "Invalid finclaw.yml configuration:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(msg)


def _validate_range(
    value: float, name: str, low: float, high: float, errors: List[str]
) -> None:
    """Validate a numeric value is within [low, high]."""
    if not (low <= value <= high):
        errors.append(f"{name} must be between {low} and {high}, got {value}")


def _validate_type(value: Any, name: str, expected: type, errors: List[str]) -> bool:
    """Validate type and append error if wrong. Returns True if valid."""
    if not isinstance(value, expected):
        errors.append(f"{name} must be {expected.__name__}, got {type(value).__name__}")
        return False
    return True


@dataclass
class BacktestConfig:
    start: str = "2020-01-01"
    end: str = ""
    initial_capital: float = 100000
    commission: float = 0.001
    slippage: float = 0.0005
    period: str = "5y"


@dataclass
class RiskConfig:
    max_position_pct: float = 0.10
    max_drawdown_pct: float = 0.20
    stop_loss_pct: float = 0.05


@dataclass
class CacheConfig:
    backend: str = "sqlite"
    ttl_seconds: int = 3600
    db_path: str = ".finclaw_cache/cache.db"


@dataclass
class ReportConfig:
    output_dir: str = "reports"
    format: str = "html"
    theme: str = "dark"


VALID_STRATEGIES = {
    "momentum", "mean_reversion", "trend_following", "pairs_trading",
    "value_momentum", "druckenmiller", "soros", "lynch", "buffett",
    "dalio", "aggressive", "balanced", "conservative",
}

VALID_UNIVERSES = {"us", "china", "hk", "japan", "korea", "all"}
VALID_CACHE_BACKENDS = {"sqlite", "memory"}
VALID_REPORT_FORMATS = {"html", "json"}
VALID_THEMES = {"dark", "light"}


@dataclass
class FinClawConfig:
    default_strategy: str = "momentum"
    default_universe: str = "us"
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    def validate(self) -> None:
        """Validate all config values. Raises ConfigValidationError on failure."""
        errors: List[str] = []

        # Strategy / universe
        if self.default_strategy not in VALID_STRATEGIES:
            errors.append(
                f"default_strategy '{self.default_strategy}' is not valid. "
                f"Choose from: {', '.join(sorted(VALID_STRATEGIES))}"
            )
        if self.default_universe not in VALID_UNIVERSES:
            errors.append(
                f"default_universe '{self.default_universe}' is not valid. "
                f"Choose from: {', '.join(sorted(VALID_UNIVERSES))}"
            )

        # Backtest ranges
        _validate_range(self.backtest.commission, "backtest.commission", 0.0, 1.0, errors)
        _validate_range(self.backtest.slippage, "backtest.slippage", 0.0, 1.0, errors)
        if self.backtest.initial_capital <= 0:
            errors.append("backtest.initial_capital must be positive")

        # Risk ranges
        _validate_range(self.risk.max_position_pct, "risk.max_position_pct", 0.0, 1.0, errors)
        _validate_range(self.risk.max_drawdown_pct, "risk.max_drawdown_pct", 0.0, 1.0, errors)
        _validate_range(self.risk.stop_loss_pct, "risk.stop_loss_pct", 0.0, 1.0, errors)

        # Cache
        if self.cache.backend not in VALID_CACHE_BACKENDS:
            errors.append(f"cache.backend must be one of {VALID_CACHE_BACKENDS}")
        if self.cache.ttl_seconds < 0:
            errors.append("cache.ttl_seconds must be non-negative")

        # Report
        if self.report.format not in VALID_REPORT_FORMATS:
            errors.append(f"report.format must be one of {VALID_REPORT_FORMATS}")

        if errors:
            raise ConfigValidationError(errors)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "FinClawConfig":
        """Load config from YAML file. Falls back to defaults. Validates on load."""
        if path is None:
            candidates = [
                os.path.join(os.getcwd(), "finclaw.yml"),
                os.path.expanduser("~/.finclaw.yml"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    path = c
                    break

        if path and os.path.exists(path):
            config = cls._from_file(path)
        else:
            config = cls()

        config.validate()
        return config

    @classmethod
    def _from_file(cls, path: str) -> "FinClawConfig":
        if not HAS_YAML:
            return cls()

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigValidationError([f"Failed to parse YAML: {e}"])
        except OSError as e:
            raise ConfigValidationError([f"Failed to read config file: {e}"])

        if not isinstance(raw, dict):
            raise ConfigValidationError(["Config file must contain a YAML mapping (dict)"])

        config = cls()
        config.default_strategy = raw.get("default_strategy", config.default_strategy)
        config.default_universe = raw.get("default_universe", config.default_universe)

        if "backtest" in raw:
            b = raw["backtest"]
            if not isinstance(b, dict):
                raise ConfigValidationError(["'backtest' must be a mapping"])
            try:
                config.backtest = BacktestConfig(
                    start=str(b.get("start", config.backtest.start)),
                    end=str(b.get("end", config.backtest.end)),
                    initial_capital=float(b.get("initial_capital", config.backtest.initial_capital)),
                    commission=float(b.get("commission", config.backtest.commission)),
                    slippage=float(b.get("slippage", config.backtest.slippage)),
                    period=str(b.get("period", config.backtest.period)),
                )
            except (ValueError, TypeError) as e:
                raise ConfigValidationError([f"Invalid backtest config value: {e}"])

        if "risk" in raw:
            r = raw["risk"]
            if not isinstance(r, dict):
                raise ConfigValidationError(["'risk' must be a mapping"])
            try:
                config.risk = RiskConfig(
                    max_position_pct=float(r.get("max_position_pct", config.risk.max_position_pct)),
                    max_drawdown_pct=float(r.get("max_drawdown_pct", config.risk.max_drawdown_pct)),
                    stop_loss_pct=float(r.get("stop_loss_pct", config.risk.stop_loss_pct)),
                )
            except (ValueError, TypeError) as e:
                raise ConfigValidationError([f"Invalid risk config value: {e}"])

        if "cache" in raw:
            c = raw["cache"]
            if not isinstance(c, dict):
                raise ConfigValidationError(["'cache' must be a mapping"])
            try:
                config.cache = CacheConfig(
                    backend=str(c.get("backend", config.cache.backend)),
                    ttl_seconds=int(c.get("ttl_seconds", config.cache.ttl_seconds)),
                    db_path=str(c.get("db_path", config.cache.db_path)),
                )
            except (ValueError, TypeError) as e:
                raise ConfigValidationError([f"Invalid cache config value: {e}"])

        if "report" in raw:
            rp = raw["report"]
            if not isinstance(rp, dict):
                raise ConfigValidationError(["'report' must be a mapping"])
            config.report = ReportConfig(
                output_dir=str(rp.get("output_dir", config.report.output_dir)),
                format=str(rp.get("format", config.report.format)),
                theme=str(rp.get("theme", config.report.theme)),
            )

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "default_strategy": self.default_strategy,
            "default_universe": self.default_universe,
            "backtest": {
                "start": self.backtest.start,
                "end": self.backtest.end,
                "initial_capital": self.backtest.initial_capital,
                "commission": self.backtest.commission,
                "slippage": self.backtest.slippage,
                "period": self.backtest.period,
            },
            "risk": {
                "max_position_pct": self.risk.max_position_pct,
                "max_drawdown_pct": self.risk.max_drawdown_pct,
                "stop_loss_pct": self.risk.stop_loss_pct,
            },
            "cache": {
                "backend": self.cache.backend,
                "ttl_seconds": self.cache.ttl_seconds,
                "db_path": self.cache.db_path,
            },
            "report": {
                "output_dir": self.report.output_dir,
                "format": self.report.format,
                "theme": self.report.theme,
            },
        }
