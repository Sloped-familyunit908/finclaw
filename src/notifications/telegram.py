"""Telegram Bot API notification channel."""

from __future__ import annotations

import logging

import requests

from .base import NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    """Send notifications via Telegram Bot API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "HTML", timeout: int = 10):
        self._token = bot_token
        self._chat_id = chat_id
        self._parse_mode = parse_mode
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "telegram"

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        icons = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.CRITICAL: "🚨",
        }
        icon = icons.get(level, "•")
        text = f"{icon} <b>[{level.value.upper()}]</b>\n{message}"
        url = self.API_URL.format(token=self._token)
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": self._parse_mode,
        }
        try:
            resp = requests.post(url, json=payload, timeout=self._timeout)
            if resp.ok:
                return True
            logger.warning("Telegram send failed %d: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as e:
            logger.error("Telegram error: %s", e)
            return False
