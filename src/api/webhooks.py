"""
FinClaw Webhook Integration
Send notifications on trading events to external services.
Supports JSON, Slack, Discord, and Teams webhook formats.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

VALID_EVENTS = {"signal_change", "alert_triggered", "trade_executed", "daily_summary"}
VALID_FORMATS = {"json", "slack", "discord", "teams"}


@dataclass
class WebhookConfig:
    url: str
    event: str
    format: str = "json"
    active: bool = True


class WebhookManager:
    """Manage and dispatch webhook notifications."""

    def __init__(self) -> None:
        self._webhooks: list[WebhookConfig] = []
        self._history: list[dict] = []

    def register(self, event: str, url: str, format: str = "json") -> WebhookConfig:
        """Register a webhook for an event type."""
        if event not in VALID_EVENTS:
            raise ValueError(f"Unknown event: {event}. Valid: {VALID_EVENTS}")
        if format not in VALID_FORMATS:
            raise ValueError(f"Unknown format: {format}. Valid: {VALID_FORMATS}")
        hook = WebhookConfig(url=url, event=event, format=format)
        self._webhooks.append(hook)
        return hook

    def unregister(self, url: str, event: str | None = None) -> int:
        """Remove webhooks matching url (and optionally event). Returns count removed."""
        before = len(self._webhooks)
        self._webhooks = [
            w for w in self._webhooks
            if not (w.url == url and (event is None or w.event == event))
        ]
        return before - len(self._webhooks)

    def list_webhooks(self) -> list[WebhookConfig]:
        return list(self._webhooks)

    def dispatch(self, event: str, payload: dict[str, Any]) -> list[dict]:
        """Send payload to all webhooks registered for this event. Returns delivery results."""
        results = []
        for hook in self._webhooks:
            if hook.event != event or not hook.active:
                continue
            body = self._format_payload(hook.format, event, payload)
            result = self._send(hook.url, body)
            result["event"] = event
            result["url"] = hook.url
            results.append(result)
            self._history.append(result)
        return results

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]

    @staticmethod
    def _format_payload(fmt: str, event: str, payload: dict) -> bytes:
        """Format payload for the target webhook service."""
        if fmt == "slack":
            text = f"🦀 *FinClaw — {event}*\n"
            for k, v in payload.items():
                text += f"• {k}: {v}\n"
            data = {"text": text}
        elif fmt == "discord":
            desc = "\n".join(f"**{k}**: {v}" for k, v in payload.items())
            data = {"embeds": [{"title": f"FinClaw — {event}", "description": desc}]}
        elif fmt == "teams":
            facts = [{"name": k, "value": str(v)} for k, v in payload.items()]
            data = {
                "@type": "MessageCard",
                "summary": f"FinClaw — {event}",
                "sections": [{"facts": facts}],
            }
        else:  # json
            data = {"event": event, "timestamp": time.time(), "data": payload}
        return json.dumps(data, default=str).encode("utf-8")

    @staticmethod
    def _send(url: str, body: bytes) -> dict:
        """Send HTTP POST to webhook URL."""
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"status": resp.status, "success": True}
        except Exception as exc:
            logger.warning("Webhook delivery failed to %s: %s", url, exc)
            return {"status": 0, "success": False, "error": str(exc)}
