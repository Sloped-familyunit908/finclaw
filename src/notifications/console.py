"""Console notification channel — stdout/stderr output."""

from __future__ import annotations

import sys
from datetime import datetime

from .base import NotificationChannel, NotificationLevel


class ConsoleChannel(NotificationChannel):
    """Print notifications to console (default channel)."""

    def __init__(self, use_stderr: bool = False, color: bool = True):
        self._stream = sys.stderr if use_stderr else sys.stdout
        self._color = color
        self._history: list[dict] = []

    @property
    def name(self) -> str:
        return "console"

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        icons = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.CRITICAL: "🚨",
        }
        icon = icons.get(level, "•")
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {icon} [{level.value.upper()}] {message}"
        try:
            self._stream.write(line + "\n")
            self._stream.flush()
            self._history.append({"time": ts, "level": level.value, "message": message})
            return True
        except Exception:
            return False
