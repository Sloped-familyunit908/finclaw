"""Base classes for the notification system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum


class NotificationLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name identifier."""

    @abstractmethod
    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        """Send a message. Returns True on success."""

    def test(self) -> bool:
        """Send a test message to verify the channel works."""
        return self.send("🦀 FinClaw test notification — channel is working!", NotificationLevel.INFO)
