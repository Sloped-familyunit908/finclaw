"""Notification channels for the smart alert system."""

from __future__ import annotations

import json
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from .engine import AlertChannel, FiredAlert


class ConsoleChannel(AlertChannel):
    """Print alerts to the terminal."""
    name = "console"

    def __init__(self, colorize: bool = True):
        self.colorize = colorize
        self.sent: list[FiredAlert] = []

    def send(self, alert: FiredAlert) -> bool:
        icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(alert.severity.value, "•")
        ts = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] {icon} [{alert.severity.value.upper()}] {alert.message}"
        print(msg)
        self.sent.append(alert)
        return True


class WebhookChannel(AlertChannel):
    """POST alert as JSON to a webhook URL."""
    name = "webhook"

    def __init__(self, url: str, headers: dict[str, str] | None = None, timeout: int = 10):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
        self.sent: list[FiredAlert] = []

    def send(self, alert: FiredAlert) -> bool:
        payload = {
            "symbol": alert.symbol,
            "condition": alert.condition,
            "value": str(alert.value),
            "threshold": alert.threshold,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.url, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self.sent.append(alert)
                return resp.status == 200
        except Exception:
            return False


class FileChannel(AlertChannel):
    """Append alerts to a log file."""
    name = "file"

    def __init__(self, path: str | Path = "alerts.log"):
        self.path = Path(path)
        self.sent: list[FiredAlert] = []

    def send(self, alert: FiredAlert) -> bool:
        entry = {
            "symbol": alert.symbol,
            "condition": alert.condition,
            "value": str(alert.value),
            "threshold": alert.threshold,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self.sent.append(alert)
            return True
        except Exception:
            return False


class EmailChannel(AlertChannel):
    """Send alert via SMTP email."""
    name = "email"

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str,
                 from_addr: str, to_addrs: list[str], use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls
        self.sent: list[FiredAlert] = []

    def send(self, alert: FiredAlert) -> bool:
        subject = f"[FinClaw Alert] {alert.severity.value.upper()}: {alert.symbol} - {alert.condition}"
        body = (
            f"Symbol: {alert.symbol}\n"
            f"Condition: {alert.condition}\n"
            f"Value: {alert.value}\n"
            f"Threshold: {alert.threshold}\n"
            f"Severity: {alert.severity.value}\n"
            f"Message: {alert.message}\n"
            f"Time: {alert.timestamp.isoformat()}\n"
        )
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = ", ".join(self.to_addrs)

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            server.quit()
            self.sent.append(alert)
            return True
        except Exception:
            return False
