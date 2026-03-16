"""Alert Manager — rule-based alert system with built-in market condition detectors."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A triggered alert."""
    name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AlertRule:
    """A registered alert rule."""
    name: str
    condition: Callable[[dict], Alert | None]
    action: str  # "log", "notify", "email", "webhook"
    enabled: bool = True


class AlertManager:
    """Register rules, check data against them, format results."""

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._history: list[Alert] = []

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, name: str, condition: Callable[[dict], Alert | None], action: str = "log") -> None:
        """Register a named alert rule."""
        self._rules.append(AlertRule(name=name, condition=condition, action=action))

    def remove_rule(self, name: str) -> bool:
        for i, r in enumerate(self._rules):
            if r.name == name:
                self._rules.pop(i)
                return True
        return False

    def enable_rule(self, name: str, enabled: bool = True) -> None:
        for r in self._rules:
            if r.name == name:
                r.enabled = enabled

    @property
    def rules(self) -> list[AlertRule]:
        return list(self._rules)

    @property
    def history(self) -> list[Alert]:
        return list(self._history)

    # ------------------------------------------------------------------
    # Checking
    # ------------------------------------------------------------------

    def check(self, data: dict) -> list[Alert]:
        """Evaluate all enabled rules against *data*, return triggered alerts."""
        triggered: list[Alert] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            try:
                result = rule.condition(data)
                if result is not None:
                    triggered.append(result)
            except Exception:
                pass  # Silently skip broken rules
        self._history.extend(triggered)
        return triggered

    def check_all(self, data_points: list[dict]) -> list[Alert]:
        """Check multiple data points, return all triggered alerts."""
        all_alerts: list[Alert] = []
        for d in data_points:
            all_alerts.extend(self.check(d))
        return all_alerts

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def format_alerts(alerts: list[Alert]) -> str:
        """Format alerts as a human-readable string."""
        if not alerts:
            return "✅ No alerts triggered."
        lines = [f"⚠️ {len(alerts)} alert(s) triggered:\n"]
        for a in alerts:
            icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(a.severity.value, "•")
            lines.append(f"  {icon} [{a.severity.value.upper()}] {a.name}: {a.message}")
            lines.append(f"     Value: {a.value:.4f} | Threshold: {a.threshold:.4f}")
        return "\n".join(lines)

    def clear_history(self) -> None:
        self._history.clear()


# ======================================================================
# Built-in rule factories
# ======================================================================

def drawdown_alert(threshold: float = 0.10) -> Callable[[dict], Alert | None]:
    """Alert when drawdown exceeds *threshold* (e.g. 0.10 = 10%)."""
    def _check(data: dict) -> Alert | None:
        equity = data.get("equity", [])
        if len(equity) < 2:
            return None
        peak = max(equity)
        current = equity[-1]
        dd = (peak - current) / peak if peak > 0 else 0.0
        if dd >= threshold:
            return Alert(
                name="Drawdown Alert",
                severity=AlertSeverity.CRITICAL if dd >= threshold * 2 else AlertSeverity.WARNING,
                message=f"Drawdown at {dd:.1%} exceeds {threshold:.1%} threshold",
                value=dd,
                threshold=threshold,
            )
        return None
    return _check


def volatility_spike(threshold: float = 2.0) -> Callable[[dict], Alert | None]:
    """Alert when recent vol exceeds *threshold* × long-term vol."""
    def _check(data: dict) -> Alert | None:
        returns = data.get("returns", [])
        if len(returns) < 42:
            return None
        recent = returns[-21:]
        long_term = returns[:-21]
        recent_std = _std(recent)
        lt_std = _std(long_term)
        if lt_std <= 0:
            return None
        ratio = recent_std / lt_std
        if ratio >= threshold:
            return Alert(
                name="Volatility Spike",
                severity=AlertSeverity.WARNING,
                message=f"Recent vol {ratio:.2f}x long-term average",
                value=ratio,
                threshold=threshold,
            )
        return None
    return _check


def correlation_break(threshold: float = 0.3) -> Callable[[dict], Alert | None]:
    """Alert when rolling correlation drops below *threshold*."""
    def _check(data: dict) -> Alert | None:
        returns = data.get("returns", [])
        benchmark_returns = data.get("benchmark_returns", [])
        n = min(len(returns), len(benchmark_returns))
        if n < 30:
            return None
        r = returns[-30:]
        b = benchmark_returns[-30:]
        corr = _correlation(r, b)
        if corr < threshold:
            return Alert(
                name="Correlation Break",
                severity=AlertSeverity.INFO,
                message=f"30-day correlation {corr:.3f} below {threshold:.3f}",
                value=corr,
                threshold=threshold,
            )
        return None
    return _check


def volume_anomaly(threshold: float = 3.0) -> Callable[[dict], Alert | None]:
    """Alert when volume is *threshold* × the 20-day average."""
    def _check(data: dict) -> Alert | None:
        volume = data.get("volume", [])
        if len(volume) < 21:
            return None
        avg = sum(volume[-21:-1]) / 20
        if avg <= 0:
            return None
        ratio = volume[-1] / avg
        if ratio >= threshold:
            return Alert(
                name="Volume Anomaly",
                severity=AlertSeverity.WARNING,
                message=f"Volume {ratio:.1f}x the 20-day average",
                value=ratio,
                threshold=threshold,
            )
        return None
    return _check


# ------------------------------------------------------------------
# Math helpers
# ------------------------------------------------------------------

def _std(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _correlation(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n < 2:
        return 0.0
    ma = sum(a[:n]) / n
    mb = sum(b[:n]) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (n - 1)
    sa = _std(a[:n])
    sb = _std(b[:n])
    if sa == 0 or sb == 0:
        return 0.0
    return cov / (sa * sb)
