"""FinClaw Notifications v4.4.0 — Multi-channel notification hub & smart alerts."""

from .base import NotificationChannel, NotificationLevel
from .hub import NotificationHub
from .console import ConsoleChannel
from .telegram import TelegramChannel
from .discord import DiscordChannel
from .email_channel import EmailChannel
from .webhook import WebhookChannel, WebhookNotifier
from .smart_alerts import SmartAlertEngine, AlertRule

__all__ = [
    "NotificationChannel",
    "NotificationLevel",
    "NotificationHub",
    "ConsoleChannel",
    "TelegramChannel",
    "DiscordChannel",
    "EmailChannel",
    "WebhookChannel",
    "WebhookNotifier",
    "SmartAlertEngine",
    "AlertRule",
]
