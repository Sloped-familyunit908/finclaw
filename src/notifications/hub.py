"""NotificationHub — central dispatcher for multi-channel notifications."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .base import NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)


class NotificationHub:
    """Central hub that routes messages to registered channels."""

    def __init__(self):
        self.channels: dict[str, NotificationChannel] = {}
        self._history: list[dict] = []

    def register_channel(self, name: str, channel: NotificationChannel) -> None:
        """Register a notification channel."""
        self.channels[name] = channel

    def unregister_channel(self, name: str) -> bool:
        """Remove a channel. Returns True if it existed."""
        return self.channels.pop(name, None) is not None

    def send(
        self,
        message: str,
        level: str = "info",
        channels: list[str] | None = None,
    ) -> dict[str, bool]:
        """
        Send a message to specified channels (or all if None).
        Returns {channel_name: success}.
        """
        lvl = NotificationLevel(level)
        targets = channels or list(self.channels.keys())
        results: dict[str, bool] = {}
        for name in targets:
            ch = self.channels.get(name)
            if ch is None:
                results[name] = False
                continue
            try:
                results[name] = ch.send(message, lvl)
            except Exception as e:
                logger.error("Channel %s error: %s", name, e)
                results[name] = False
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "level": level,
            "results": results,
        })
        return results

    def send_alert(self, alert: Any) -> dict[str, bool]:
        """Send an Alert object to all channels."""
        level = getattr(alert, "severity", None)
        if level is not None:
            level = level.value if hasattr(level, "value") else str(level)
        else:
            level = "info"
        message = getattr(alert, "message", str(alert))
        name = getattr(alert, "name", "Alert")
        text = f"[{name}] {message}"
        return self.send(text, level=level)

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
