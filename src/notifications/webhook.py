"""
FinClaw Webhook Notifier v4.4.0
Send notifications to Slack, Discord, and custom webhook endpoints.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from .base import NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)


class WebhookChannel(NotificationChannel):
    """Generic webhook channel implementing NotificationChannel interface."""

    def __init__(self, url: str, headers: dict | None = None, timeout: int = 10):
        self._url = url
        self._headers = {"Content-Type": "application/json", **(headers or {})}
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "webhook"

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        payload = {
            "text": message,
            "level": level.value,
            "source": "finclaw",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        try:
            resp = requests.post(self._url, json=payload, headers=self._headers, timeout=self._timeout)
            return 200 <= resp.status_code < 300
        except Exception as e:
            logger.error("Webhook error: %s", e)
            return False


class WebhookNotifier:
    """
    Multi-platform webhook notifier.

    Supports Slack, Discord, and generic JSON webhooks.
    """

    def __init__(self, webhooks: dict[str, str], timeout: int = 10):
        """
        Args:
            webhooks: Mapping of platform → URL.
                      Keys: 'slack', 'discord', 'custom', or any name.
            timeout: HTTP request timeout in seconds.
        """
        self.webhooks = dict(webhooks)
        self.timeout = timeout
        self._formatters = {
            "slack": self.format_slack,
            "discord": self.format_discord,
        }

    def notify(self, event: str, data: dict) -> dict[str, bool]:
        """
        Send notification to all configured webhooks.

        Returns dict of {platform: success_bool}.
        """
        results = {}
        enriched = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        }
        for platform, url in self.webhooks.items():
            formatter = self._formatters.get(platform)
            payload = formatter(enriched) if formatter else enriched
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )
                success = 200 <= resp.status_code < 300
                results[platform] = success
                if not success:
                    logger.warning(
                        "Webhook %s returned %d: %s",
                        platform, resp.status_code, resp.text[:200],
                    )
            except Exception as e:
                logger.error("Webhook %s failed: %s", platform, e)
                results[platform] = False
        return results

    def format_slack(self, data: dict) -> dict:
        """Format payload for Slack Incoming Webhooks."""
        event = data.get("event", "notification")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🦀 FinClaw: {event}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*{k}:*\n{v}"}
                    for k, v in data.items()
                    if k not in ("event", "timestamp")
                ][:10],
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"⏰ {data.get('timestamp', '')}"}
                ],
            },
        ]
        return {"blocks": blocks, "text": f"FinClaw: {event}"}

    def format_discord(self, data: dict) -> dict:
        """Format payload for Discord Webhooks."""
        event = data.get("event", "notification")
        fields = [
            {"name": k, "value": str(v)[:1024], "inline": True}
            for k, v in data.items()
            if k not in ("event", "timestamp")
        ][:25]
        return {
            "embeds": [
                {
                    "title": f"🦀 FinClaw: {event}",
                    "color": 0x00D4AA,
                    "fields": fields,
                    "footer": {"text": data.get("timestamp", "")},
                }
            ]
        }

    def add_webhook(self, platform: str, url: str):
        """Add or update a webhook endpoint."""
        self.webhooks[platform] = url

    def remove_webhook(self, platform: str):
        """Remove a webhook endpoint."""
        self.webhooks.pop(platform, None)
