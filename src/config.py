"""
FinClaw Configuration
Load settings from finclaw.yml with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


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


@dataclass
class FinClawConfig:
    default_strategy: str = "momentum"
    default_universe: str = "us"
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "FinClawConfig":
        """Load config from YAML file. Falls back to defaults."""
        if path is None:
            # Search order: ./finclaw.yml, ~/.finclaw.yml
            candidates = [
                os.path.join(os.getcwd(), "finclaw.yml"),
                os.path.expanduser("~/.finclaw.yml"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    path = c
                    break

        if path and os.path.exists(path):
            return cls._from_file(path)
        return cls()

    @classmethod
    def _from_file(cls, path: str) -> "FinClawConfig":
        if not HAS_YAML:
            # Fallback: simple key-value parse for flat configs
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        config = cls()
        config.default_strategy = raw.get("default_strategy", config.default_strategy)
        config.default_universe = raw.get("default_universe", config.default_universe)

        if "backtest" in raw:
            b = raw["backtest"]
            config.backtest = BacktestConfig(
                start=b.get("start", config.backtest.start),
                end=b.get("end", config.backtest.end),
                initial_capital=float(b.get("initial_capital", config.backtest.initial_capital)),
                commission=float(b.get("commission", config.backtest.commission)),
                slippage=float(b.get("slippage", config.backtest.slippage)),
                period=b.get("period", config.backtest.period),
            )

        if "risk" in raw:
            r = raw["risk"]
            config.risk = RiskConfig(
                max_position_pct=float(r.get("max_position_pct", config.risk.max_position_pct)),
                max_drawdown_pct=float(r.get("max_drawdown_pct", config.risk.max_drawdown_pct)),
                stop_loss_pct=float(r.get("stop_loss_pct", config.risk.stop_loss_pct)),
            )

        if "cache" in raw:
            c = raw["cache"]
            config.cache = CacheConfig(
                backend=c.get("backend", config.cache.backend),
                ttl_seconds=int(c.get("ttl_seconds", config.cache.ttl_seconds)),
                db_path=c.get("db_path", config.cache.db_path),
            )

        if "report" in raw:
            rp = raw["report"]
            config.report = ReportConfig(
                output_dir=rp.get("output_dir", config.report.output_dir),
                format=rp.get("format", config.report.format),
                theme=rp.get("theme", config.report.theme),
            )

        return config

    def to_dict(self) -> dict[str, Any]:
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
