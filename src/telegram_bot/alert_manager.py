"""
FinClaw Alert Manager for Telegram Bot
=======================================
Manages price alerts and sends notifications when conditions are met.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.telegram_bot.bot import TelegramBot

logger = logging.getLogger(__name__)

ALERTS_FILE = os.path.join(os.path.expanduser("~"), ".finclaw", "telegram_alerts.json")


@dataclass
class PriceAlert:
    id: int
    chat_id: int | str
    symbol: str
    operator: str  # >, <, >=, <=
    threshold: float
    created_at: float = field(default_factory=time.time)
    triggered: bool = False
    cooldown: int = 3600  # seconds between re-triggers

    def check(self, price: float) -> bool:
        ops = {">": price > self.threshold, "<": price < self.threshold,
               ">=": price >= self.threshold, "<=": price <= self.threshold}
        return ops.get(self.operator, False)

    def to_dict(self) -> dict:
        return {"id": self.id, "chat_id": self.chat_id, "symbol": self.symbol,
                "operator": self.operator, "threshold": self.threshold,
                "created_at": self.created_at, "triggered": self.triggered,
                "cooldown": self.cooldown}

    @classmethod
    def from_dict(cls, d: dict) -> "PriceAlert":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class AlertManager:
    """Manages price alerts with persistence and periodic checking."""

    def __init__(self, bot: "TelegramBot"):
        self.bot = bot
        self.alerts: list[PriceAlert] = []
        self._next_id = 1
        self._last_triggered: dict[int, float] = {}
        self._check_interval = 60  # seconds
        self._load()

    def _load(self):
        if os.path.exists(ALERTS_FILE):
            try:
                with open(ALERTS_FILE) as f:
                    data = json.load(f)
                self.alerts = [PriceAlert.from_dict(d) for d in data.get("alerts", [])]
                self._next_id = data.get("next_id", 1)
            except Exception:
                pass

    def _save(self):
        os.makedirs(os.path.dirname(ALERTS_FILE), exist_ok=True)
        data = {"alerts": [a.to_dict() for a in self.alerts], "next_id": self._next_id}
        with open(ALERTS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def add_alert(self, chat_id: int | str, symbol: str, operator: str, threshold: float) -> int:
        alert = PriceAlert(id=self._next_id, chat_id=chat_id, symbol=symbol,
                           operator=operator, threshold=threshold)
        self.alerts.append(alert)
        self._next_id += 1
        self._save()
        return alert.id

    def remove_alert(self, alert_id: int) -> bool:
        before = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.id != alert_id]
        if len(self.alerts) < before:
            self._save()
            return True
        return False

    def get_alerts(self, chat_id: int | str | None = None) -> list[dict]:
        alerts = self.alerts if chat_id is None else [a for a in self.alerts if a.chat_id == chat_id]
        return [a.to_dict() for a in alerts if not a.triggered]

    async def check_once(self):
        """Check all alerts against current prices."""
        if not self.alerts:
            return

        # Group by symbol
        symbols = set(a.symbol for a in self.alerts if not a.triggered)
        if not symbols:
            return

        try:
            import yfinance as yf
            for symbol in symbols:
                try:
                    hist = yf.Ticker(symbol).history(period="1d")
                    if hist.empty:
                        continue
                    price = float(hist["Close"].iloc[-1])
                except Exception:
                    continue

                for alert in self.alerts:
                    if alert.symbol != symbol or alert.triggered:
                        continue
                    # Cooldown check
                    last = self._last_triggered.get(alert.id, 0)
                    if time.time() - last < alert.cooldown:
                        continue

                    if alert.check(price):
                        alert.triggered = True
                        self._last_triggered[alert.id] = time.time()
                        self._save()
                        msg = (f"🔔 *Alert Triggered!*\n\n"
                               f"{alert.symbol}: ${price:.2f} {alert.operator} {alert.threshold}")
                        try:
                            await self.bot.send_message(alert.chat_id, msg)
                        except Exception as e:
                            logger.error("Failed to send alert: %s", e)
        except ImportError:
            logger.warning("yfinance not available for alert checking")

    async def check_loop(self):
        """Continuous alert checking loop."""
        while True:
            try:
                await self.check_once()
            except Exception as e:
                logger.error("Alert check error: %s", e)
            await asyncio.sleep(self._check_interval)
