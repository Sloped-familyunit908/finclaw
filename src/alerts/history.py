"""Alert history — persistence and analytics for fired alerts."""

from __future__ import annotations

import json
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .engine import FiredAlert, AlertSeverity, AlertRule, AlertCondition


class AlertHistory:
    """Track, query, and export alert history."""

    def __init__(self, persist_path: str | Path | None = None):
        self._alerts: list[FiredAlert] = []
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    def record(self, alert: FiredAlert) -> None:
        """Record a fired alert."""
        self._alerts.append(alert)
        if self._persist_path:
            self._save()

    def record_many(self, alerts: list[FiredAlert]) -> None:
        for a in alerts:
            self._alerts.append(a)
        if self._persist_path and alerts:
            self._save()

    def get_recent(self, hours: int = 24) -> list[FiredAlert]:
        """Get alerts from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [a for a in self._alerts if a.timestamp >= cutoff]

    def get_by_symbol(self, symbol: str) -> list[FiredAlert]:
        return [a for a in self._alerts if a.symbol == symbol]

    def get_by_severity(self, severity: AlertSeverity) -> list[FiredAlert]:
        return [a for a in self._alerts if a.severity == severity]

    def get_by_condition(self, condition: str) -> list[FiredAlert]:
        return [a for a in self._alerts if a.condition == condition]

    def get_stats(self) -> dict:
        """Return stats: total, by_type, by_severity, by_symbol."""
        stats: dict[str, Any] = {
            "total": len(self._alerts),
            "by_condition": {},
            "by_severity": {},
            "by_symbol": {},
        }
        for a in self._alerts:
            stats["by_condition"][a.condition] = stats["by_condition"].get(a.condition, 0) + 1
            stats["by_severity"][a.severity.value] = stats["by_severity"].get(a.severity.value, 0) + 1
            stats["by_symbol"][a.symbol] = stats["by_symbol"].get(a.symbol, 0) + 1
        return stats

    def clear(self) -> None:
        self._alerts.clear()
        if self._persist_path and self._persist_path.exists():
            self._persist_path.unlink()

    def export(self, format: str = "json") -> str:
        """Export history as json or csv."""
        records = [self._to_dict(a) for a in self._alerts]
        if format == "csv":
            if not records:
                return ""
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
            return buf.getvalue()
        return json.dumps(records, indent=2, default=str)

    @property
    def all_alerts(self) -> list[FiredAlert]:
        return list(self._alerts)

    def __len__(self) -> int:
        return len(self._alerts)

    # ---- persistence ----

    @staticmethod
    def _to_dict(a: FiredAlert) -> dict:
        return {
            "symbol": a.symbol,
            "condition": a.condition,
            "value": str(a.value),
            "threshold": a.threshold,
            "severity": a.severity.value,
            "message": a.message,
            "timestamp": a.timestamp.isoformat(),
        }

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump([self._to_dict(a) for a in self._alerts], f, default=str)

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for d in data:
                # Reconstruct minimal FiredAlert
                rule = AlertRule(
                    name="loaded",
                    condition=AlertCondition(d["condition"]),
                    symbol=d["symbol"],
                    threshold=d["threshold"],
                )
                alert = FiredAlert(
                    rule=rule,
                    symbol=d["symbol"],
                    condition=d["condition"],
                    value=d["value"],
                    threshold=d["threshold"],
                    severity=AlertSeverity(d["severity"]),
                    message=d["message"],
                    timestamp=datetime.fromisoformat(d["timestamp"]),
                )
                self._alerts.append(alert)
        except Exception:
            pass
