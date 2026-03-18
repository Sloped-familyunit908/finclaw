"""SmartAlertEngine — advanced rule-based alert system with built-in market detectors."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """A smart alert rule."""
    name: str
    rule_type: str
    params: dict
    condition: Callable[[dict], Optional[dict]]
    enabled: bool = True
    cooldown_seconds: int = 0
    last_triggered: Optional[datetime] = None


class SmartAlertEngine:
    """
    Advanced alert engine with built-in market condition detectors.

    Supports price crosses, volume spikes, drawdown alerts,
    correlation breaks, P&L targets, and risk breaches.
    """

    def __init__(self):
        self._rules: list[AlertRule] = []
        self._history: list[dict] = []

    @property
    def rules(self) -> list[AlertRule]:
        return list(self._rules)

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def add_rule(self, rule: AlertRule) -> None:
        """Register a custom alert rule."""
        self._rules.append(rule)

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

    def evaluate(self, data: dict) -> list[dict]:
        """Evaluate all enabled rules against data. Returns list of triggered alert dicts."""
        triggered = []
        now = datetime.now()
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.cooldown_seconds > 0 and rule.last_triggered:
                elapsed = (now - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            try:
                result = rule.condition(data)
                if result is not None:
                    alert = {
                        "rule": rule.name,
                        "type": rule.rule_type,
                        "timestamp": now.isoformat(),
                        **result,
                    }
                    triggered.append(alert)
                    rule.last_triggered = now
                    self._history.append(alert)
            except Exception as e:
                logger.warning("Alert rule '%s' evaluation failed: %s", rule.name, e)
        return triggered

    # ------------------------------------------------------------------
    # Built-in rule factories
    # ------------------------------------------------------------------

    def price_cross(self, symbol: str, threshold: float, direction: str = "above") -> AlertRule:
        """Create a price-crossing alert rule."""
        def _check(data: dict) -> Optional[dict]:
            price = data.get("price")
            if price is None:
                return None
            sym = data.get("symbol", "")
            if sym and sym != symbol:
                return None
            if direction == "above" and price > threshold:
                return {"symbol": symbol, "price": price, "threshold": threshold, "direction": "above",
                        "message": f"{symbol} crossed above {threshold} (current: {price})"}
            elif direction == "below" and price < threshold:
                return {"symbol": symbol, "price": price, "threshold": threshold, "direction": "below",
                        "message": f"{symbol} crossed below {threshold} (current: {price})"}
            return None

        rule = AlertRule(
            name=f"price_cross_{symbol}_{direction}_{threshold}",
            rule_type="price_cross",
            params={"symbol": symbol, "threshold": threshold, "direction": direction},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def volume_spike(self, symbol: str, multiplier: float = 3.0) -> AlertRule:
        """Create a volume-spike alert rule."""
        def _check(data: dict) -> Optional[dict]:
            sym = data.get("symbol", "")
            if sym and sym != symbol:
                return None
            volume = data.get("volume", [])
            if len(volume) < 21:
                return None
            avg = sum(volume[-21:-1]) / 20
            if avg <= 0:
                return None
            ratio = volume[-1] / avg
            if ratio >= multiplier:
                return {"symbol": symbol, "ratio": round(ratio, 2), "multiplier": multiplier,
                        "message": f"{symbol} volume {ratio:.1f}x the 20-day average"}
            return None

        rule = AlertRule(
            name=f"volume_spike_{symbol}_{multiplier}",
            rule_type="volume_spike",
            params={"symbol": symbol, "multiplier": multiplier},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def drawdown_alert(self, portfolio: str, threshold: float = 0.10) -> AlertRule:
        """Create a drawdown alert rule."""
        def _check(data: dict) -> Optional[dict]:
            pf = data.get("portfolio", "")
            if pf and pf != portfolio:
                return None
            equity = data.get("equity", [])
            if len(equity) < 2:
                return None
            peak = max(equity)
            current = equity[-1]
            dd = (peak - current) / peak if peak > 0 else 0.0
            if dd >= threshold:
                return {"portfolio": portfolio, "drawdown": round(dd, 4), "threshold": threshold,
                        "message": f"{portfolio} drawdown at {dd:.1%} exceeds {threshold:.1%}"}
            return None

        rule = AlertRule(
            name=f"drawdown_{portfolio}_{threshold}",
            rule_type="drawdown",
            params={"portfolio": portfolio, "threshold": threshold},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def correlation_break(self, pair: tuple[str, str], threshold: float = 0.3) -> AlertRule:
        """Alert when correlation between a pair drops below threshold."""
        def _check(data: dict) -> Optional[dict]:
            returns_a = data.get("returns_a", [])
            returns_b = data.get("returns_b", [])
            n = min(len(returns_a), len(returns_b))
            if n < 30:
                return None
            corr = _correlation(returns_a[-30:], returns_b[-30:])
            if corr < threshold:
                return {"pair": list(pair), "correlation": round(corr, 4), "threshold": threshold,
                        "message": f"Correlation between {pair[0]}/{pair[1]} at {corr:.3f} below {threshold}"}
            return None

        rule = AlertRule(
            name=f"corr_break_{'_'.join(pair)}_{threshold}",
            rule_type="correlation_break",
            params={"pair": list(pair), "threshold": threshold},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def pnl_target(self, target_pct: float) -> AlertRule:
        """Alert when portfolio P&L reaches target percentage."""
        def _check(data: dict) -> Optional[dict]:
            pnl_pct = data.get("pnl_pct")
            if pnl_pct is None:
                return None
            if pnl_pct >= target_pct:
                return {"pnl_pct": round(pnl_pct, 4), "target": target_pct,
                        "message": f"P&L target reached: {pnl_pct:.2%} >= {target_pct:.2%}"}
            return None

        rule = AlertRule(
            name=f"pnl_target_{target_pct}",
            rule_type="pnl_target",
            params={"target_pct": target_pct},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def risk_breach(self, metric: str, threshold: float) -> AlertRule:
        """Alert when a risk metric exceeds threshold."""
        def _check(data: dict) -> Optional[dict]:
            value = data.get(metric)
            if value is None:
                return None
            if value > threshold:
                return {"metric": metric, "value": round(value, 4), "threshold": threshold,
                        "message": f"Risk breach: {metric} = {value:.4f} > {threshold:.4f}"}
            return None

        rule = AlertRule(
            name=f"risk_breach_{metric}_{threshold}",
            rule_type="risk_breach",
            params={"metric": metric, "threshold": threshold},
            condition=_check,
        )
        self._rules.append(rule)
        return rule

    def clear_history(self) -> None:
        self._history.clear()


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
