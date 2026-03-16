"""
FinClaw Structured Logger
Domain-specific logging for trades, signals, risk events, and performance.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": record.created,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            entry["data"] = record.extra_data
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        return json.dumps(entry, default=str)


class FinClawLogger:
    """
    Structured logger for FinClaw components.

    Usage:
        logger = FinClawLogger('backtest')
        logger.trade('BUY', 'AAPL', shares=100, price=150.25)
        logger.signal('SELL', 'MSFT', strength=-0.7, strategy='momentum')
        logger.risk('MAX_DRAWDOWN', current=-0.15, limit=-0.20)
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        json_output: bool = False,
        log_file: str | None = None,
    ):
        self.name = name
        self._logger = logging.getLogger(f"finclaw.{name}")
        self._logger.setLevel(level)
        self._records: list[dict] = []

        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            if json_output:
                handler.setFormatter(_JsonFormatter())
            else:
                handler.setFormatter(logging.Formatter(
                    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                ))
            self._logger.addHandler(handler)

            if log_file:
                fh = logging.FileHandler(log_file, encoding="utf-8")
                fh.setFormatter(_JsonFormatter())
                self._logger.addHandler(fh)

    def _emit(self, level: str, category: str, message: str, **kwargs: Any) -> dict:
        record = {
            "timestamp": time.time(),
            "category": category,
            "message": message,
            **kwargs,
        }
        self._records.append(record)

        log_fn = getattr(self._logger, level, self._logger.info)
        extra_record = logging.LogRecord(
            name=self._logger.name, level=getattr(logging, level.upper(), logging.INFO),
            pathname="", lineno=0, msg=message, args=(), exc_info=None,
        )
        extra_record.extra_data = kwargs  # type: ignore[attr-defined]
        self._logger.handle(extra_record)
        return record

    def trade(self, action: str, ticker: str, **kwargs: Any) -> dict:
        """Log a trade event."""
        msg = f"TRADE {action} {ticker}"
        return self._emit("info", "trade", msg, action=action, ticker=ticker, **kwargs)

    def signal(self, direction: str, ticker: str, **kwargs: Any) -> dict:
        """Log a signal event."""
        msg = f"SIGNAL {direction} {ticker}"
        return self._emit("info", "signal", msg, direction=direction, ticker=ticker, **kwargs)

    def risk(self, risk_type: str, **kwargs: Any) -> dict:
        """Log a risk event."""
        msg = f"RISK {risk_type}"
        return self._emit("warning", "risk", msg, risk_type=risk_type, **kwargs)

    def performance(self, metric: str, value: float, **kwargs: Any) -> dict:
        """Log a performance metric."""
        msg = f"PERF {metric}={value}"
        return self._emit("info", "performance", msg, metric=metric, value=value, **kwargs)

    def error(self, message: str, **kwargs: Any) -> dict:
        """Log an error."""
        return self._emit("error", "error", message, **kwargs)

    def get_records(self, category: str | None = None) -> list[dict]:
        """Get recorded log entries, optionally filtered by category."""
        if category:
            return [r for r in self._records if r["category"] == category]
        return list(self._records)

    def clear(self) -> None:
        """Clear recorded entries."""
        self._records.clear()
