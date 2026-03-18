"""Smart Alert Engine v5.10 — rule-based alerting with cooldowns, channels, and history."""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AlertCondition(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    VOLUME_SPIKE = "volume_spike"
    MACD_CROSS = "macd_cross"
    BOLLINGER_BREAKOUT = "bollinger_breakout"
    SENTIMENT_SHIFT = "sentiment_shift"
    DRAWDOWN = "drawdown"
    POSITION_SIZE = "position_size"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Base alert rule."""
    name: str
    condition: AlertCondition
    symbol: str
    threshold: float
    cooldown: int = 3600  # seconds
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    rule_id: int = 0


@dataclass
class PriceAlert(AlertRule):
    """Alert when price crosses a threshold."""
    direction: str = "above"  # "above" or "below"

    def __post_init__(self):
        self.condition = AlertCondition.PRICE_ABOVE if self.direction == "above" else AlertCondition.PRICE_BELOW


@dataclass
class VolumeAlert(AlertRule):
    """Alert on unusual volume spike (multiplier of 20-day avg)."""
    multiplier: float = 2.0

    def __post_init__(self):
        self.condition = AlertCondition.VOLUME_SPIKE
        if self.threshold == 0:
            self.threshold = self.multiplier


@dataclass
class TechnicalAlert(AlertRule):
    """Alert on technical indicator conditions (RSI, MACD, BB)."""
    indicator: str = "rsi"  # "rsi", "macd", "bollinger"


@dataclass
class SentimentAlert(AlertRule):
    """Alert on sentiment score shift."""
    def __post_init__(self):
        self.condition = AlertCondition.SENTIMENT_SHIFT


@dataclass
class PortfolioAlert(AlertRule):
    """Alert on portfolio drawdown or position size."""
    metric: str = "drawdown"  # "drawdown" or "position_size"

    def __post_init__(self):
        self.condition = AlertCondition.DRAWDOWN if self.metric == "drawdown" else AlertCondition.POSITION_SIZE


@dataclass
class FiredAlert:
    """Record of a triggered alert."""
    rule: AlertRule
    symbol: str
    condition: str
    value: Any
    threshold: float
    severity: AlertSeverity
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class AlertChannel:
    """Base notification channel."""
    name: str = "base"

    def send(self, alert: FiredAlert) -> bool:
        raise NotImplementedError


class AlertEngine:
    """Register rules and channels, evaluate market data, fire alerts with cooldowns."""

    def __init__(self) -> None:
        self.rules: list[AlertRule] = []
        self.channels: list[AlertChannel] = []
        self._next_id = 1
        self._last_fired: dict[int, float] = {}  # rule_id -> timestamp
        self._fired_alerts: list[FiredAlert] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def add_rule(self, rule: AlertRule) -> int:
        """Add an alert rule, return its id."""
        rule.rule_id = self._next_id
        self._next_id += 1
        self.rules.append(rule)
        return rule.rule_id

    # Alias for backwards compatibility
    add_alert = add_rule

    def remove_rule(self, rule_id: int) -> bool:
        for i, r in enumerate(self.rules):
            if r.rule_id == rule_id:
                self.rules.pop(i)
                self._last_fired.pop(rule_id, None)
                return True
        return False

    def add_channel(self, channel: AlertChannel) -> None:
        self.channels.append(channel)

    def remove_channel(self, name: str) -> bool:
        for i, c in enumerate(self.channels):
            if c.name == name:
                self.channels.pop(i)
                return True
        return False

    def _in_cooldown(self, rule: AlertRule) -> bool:
        last = self._last_fired.get(rule.rule_id)
        if last is None:
            return False
        return (time.time() - last) < rule.cooldown

    def _fire(self, rule: AlertRule, value: Any, message: str) -> FiredAlert:
        alert = FiredAlert(
            rule=rule,
            symbol=rule.symbol,
            condition=rule.condition.value,
            value=value,
            threshold=rule.threshold,
            severity=rule.severity,
            message=message,
        )
        self._last_fired[rule.rule_id] = time.time()
        self._fired_alerts.append(alert)
        for ch in self.channels:
            try:
                ch.send(alert)
            except Exception as e:
                logger.warning("Alert channel %s.send failed: %s", type(ch).__name__, e)
        return alert

    def evaluate(self, market_data: dict) -> list[FiredAlert]:
        """Evaluate all rules against market_data.

        market_data keys:
          symbol: str
          price: float
          close: list[float] (historical closes)
          volume: list[float] (historical volumes)
          sentiment: float (optional, -1 to 1)
          equity: list[float] (optional, portfolio equity curve)
          position_pct: float (optional, position as % of portfolio)
        """
        symbol = market_data.get("symbol", "")
        price = market_data.get("price", 0.0)
        close = np.array(market_data.get("close", []), dtype=float)
        volume = np.array(market_data.get("volume", []), dtype=float)
        sentiment = market_data.get("sentiment")
        equity = market_data.get("equity", [])
        position_pct = market_data.get("position_pct", 0.0)

        triggered: list[FiredAlert] = []

        for rule in self.rules:
            if not rule.enabled or rule.symbol != symbol:
                continue
            if self._in_cooldown(rule):
                continue

            try:
                alert = self._evaluate_rule(rule, price, close, volume, sentiment, equity, position_pct)
                if alert:
                    triggered.append(alert)
            except Exception as e:
                logger.warning("Rule evaluation failed for %s: %s", rule.rule_id, e)

        return triggered

    def _evaluate_rule(self, rule, price, close, volume, sentiment, equity, position_pct) -> Optional[FiredAlert]:
        cond = rule.condition
        thr = rule.threshold

        if cond == AlertCondition.PRICE_ABOVE and price > thr:
            return self._fire(rule, price, f"{rule.symbol} price {price:.2f} > {thr:.2f}")

        if cond == AlertCondition.PRICE_BELOW and price < thr:
            return self._fire(rule, price, f"{rule.symbol} price {price:.2f} < {thr:.2f}")

        if cond == AlertCondition.RSI_ABOVE and len(close) >= 15:
            from src.ta import rsi as calc_rsi
            r = float(calc_rsi(close, 14)[-1])
            if r > thr:
                return self._fire(rule, r, f"{rule.symbol} RSI {r:.1f} > {thr:.1f}")

        if cond == AlertCondition.RSI_BELOW and len(close) >= 15:
            from src.ta import rsi as calc_rsi
            r = float(calc_rsi(close, 14)[-1])
            if r < thr:
                return self._fire(rule, r, f"{rule.symbol} RSI {r:.1f} < {thr:.1f}")

        if cond == AlertCondition.VOLUME_SPIKE and len(volume) >= 21:
            avg = float(np.mean(volume[-21:-1]))
            ratio = float(volume[-1] / avg) if avg > 0 else 0
            if ratio > thr:
                return self._fire(rule, ratio, f"{rule.symbol} volume {ratio:.1f}x avg")

        if cond == AlertCondition.MACD_CROSS and len(close) >= 35:
            from src.ta import macd as calc_macd
            _, _, hist = calc_macd(close)
            if hist[-2] < 0 and hist[-1] >= 0:
                return self._fire(rule, "bullish", f"{rule.symbol} MACD bullish crossover")
            elif hist[-2] > 0 and hist[-1] <= 0:
                return self._fire(rule, "bearish", f"{rule.symbol} MACD bearish crossover")

        if cond == AlertCondition.BOLLINGER_BREAKOUT and len(close) >= 20:
            from src.ta import bollinger_bands
            bb = bollinger_bands(close)
            p = float(close[-1])
            if p > bb["upper"][-1]:
                return self._fire(rule, "above_upper", f"{rule.symbol} broke above upper BB")
            elif p < bb["lower"][-1]:
                return self._fire(rule, "below_lower", f"{rule.symbol} broke below lower BB")

        if cond == AlertCondition.SENTIMENT_SHIFT and sentiment is not None:
            if abs(sentiment) > thr:
                direction = "positive" if sentiment > 0 else "negative"
                return self._fire(rule, sentiment, f"{rule.symbol} sentiment {direction} ({sentiment:.2f})")

        if cond == AlertCondition.DRAWDOWN and len(equity) >= 2:
            peak = max(equity)
            current = equity[-1]
            dd = (peak - current) / peak if peak > 0 else 0
            if dd > thr:
                return self._fire(rule, dd, f"{rule.symbol} drawdown {dd:.1%} > {thr:.1%}")

        if cond == AlertCondition.POSITION_SIZE:
            if position_pct > thr:
                return self._fire(rule, position_pct, f"{rule.symbol} position {position_pct:.1%} > {thr:.1%}")

        return None

    @property
    def active_rules(self) -> list[AlertRule]:
        return [r for r in self.rules if r.enabled]

    @property
    def fired_alerts(self) -> list[FiredAlert]:
        return list(self._fired_alerts)

    def start(self, fetch_fn: Callable[[list[str]], list[dict]], symbols: list[str], interval: int = 60) -> None:
        """Start the alert engine loop in a background thread."""
        self._running = True

        def _loop():
            while self._running:
                try:
                    data_list = fetch_fn(symbols)
                    for data in data_list:
                        self.evaluate(data)
                except Exception as e:
                    logger.warning("Alert engine loop iteration failed: %s", e)
                time.sleep(interval)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
