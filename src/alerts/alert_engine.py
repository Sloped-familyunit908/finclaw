"""Alert Engine — monitor conditions and fire callbacks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

from src.ta import rsi as calc_rsi, macd as calc_macd, bollinger_bands


class AlertCondition(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_ABOVE = "rsi_above"
    RSI_BELOW = "rsi_below"
    VOLUME_SPIKE = "volume_spike"
    MACD_CROSS = "macd_cross"
    BOLLINGER_BREAKOUT = "bollinger_breakout"


@dataclass
class Alert:
    ticker: str
    condition: AlertCondition
    threshold: float | None
    callback: Callable[[str, str, Any], None]
    triggered: bool = False
    alert_id: int = 0


class AlertEngine:
    """Register and evaluate alerts against market data."""

    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._next_id = 1

    def add_alert(
        self,
        ticker: str,
        condition: str | AlertCondition,
        callback: Callable[[str, str, Any], None],
        threshold: float | None = None,
    ) -> int:
        """Add an alert, return alert id."""
        cond = AlertCondition(condition)
        alert = Alert(ticker=ticker, condition=cond, threshold=threshold, callback=callback, alert_id=self._next_id)
        self._alerts.append(alert)
        self._next_id += 1
        return alert.alert_id

    def remove_alert(self, alert_id: int) -> bool:
        for i, a in enumerate(self._alerts):
            if a.alert_id == alert_id:
                self._alerts.pop(i)
                return True
        return False

    def evaluate(self, ticker: str, close: np.ndarray, volume: np.ndarray | None = None) -> list[int]:
        """Evaluate all alerts for *ticker* against data. Returns list of triggered alert ids."""
        triggered: list[int] = []
        price = float(close[-1])
        for alert in self._alerts:
            if alert.ticker != ticker or alert.triggered:
                continue
            fire = False
            detail: Any = price
            thr = alert.threshold or 0.0

            if alert.condition == AlertCondition.PRICE_ABOVE and price > thr:
                fire = True
            elif alert.condition == AlertCondition.PRICE_BELOW and price < thr:
                fire = True
            elif alert.condition == AlertCondition.RSI_ABOVE and len(close) >= 15:
                r = float(calc_rsi(close, 14)[-1])
                if r > thr:
                    fire, detail = True, r
            elif alert.condition == AlertCondition.RSI_BELOW and len(close) >= 15:
                r = float(calc_rsi(close, 14)[-1])
                if r < thr:
                    fire, detail = True, r
            elif alert.condition == AlertCondition.VOLUME_SPIKE and volume is not None and len(volume) >= 21:
                avg = float(np.mean(volume[-21:-1]))
                ratio = float(volume[-1] / avg) if avg > 0 else 0
                if ratio > (thr or 2.0):
                    fire, detail = True, ratio
            elif alert.condition == AlertCondition.MACD_CROSS and len(close) >= 35:
                _, _, hist = calc_macd(close)
                if hist[-2] < 0 and hist[-1] >= 0:
                    fire, detail = True, "bullish"
                elif hist[-2] > 0 and hist[-1] <= 0:
                    fire, detail = True, "bearish"
            elif alert.condition == AlertCondition.BOLLINGER_BREAKOUT and len(close) >= 20:
                bb = bollinger_bands(close)
                if price > bb["upper"][-1]:
                    fire, detail = True, "above_upper"
                elif price < bb["lower"][-1]:
                    fire, detail = True, "below_lower"

            if fire:
                alert.triggered = True
                alert.callback(ticker, alert.condition.value, detail)
                triggered.append(alert.alert_id)
        return triggered

    @property
    def active_alerts(self) -> list[Alert]:
        return [a for a in self._alerts if not a.triggered]
