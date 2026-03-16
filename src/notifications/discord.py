"""Discord webhook notification channel."""

from __future__ import annotations

import logging

import requests

from .base import NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)


class DiscordChannel(NotificationChannel):
    """Send notifications via Discord webhook."""

    def __init__(self, webhook_url: str, username: str = "FinClaw", timeout: int = 10):
        self._url = webhook_url
        self._username = username
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "discord"

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        colors = {
            NotificationLevel.DEBUG: 0x808080,
            NotificationLevel.INFO: 0x00D4AA,
            NotificationLevel.WARNING: 0xFFAA00,
            NotificationLevel.CRITICAL: 0xFF0000,
        }
        payload = {
            "username": self._username,
            "embeds": [{
                "title": f"🦀 FinClaw [{level.value.upper()}]",
                "description": message,
                "color": colors.get(level, 0x00D4AA),
            }],
        }
        try:
            resp = requests.post(self._url, json=payload, timeout=self._timeout)
            if resp.ok or resp.status_code == 204:
                return True
            logger.warning("Discord send failed %d: %s", resp.status_code, resp.text[:200])
            return False
        except Exception as e:
            logger.error("Discord error: %s", e)
            return False
