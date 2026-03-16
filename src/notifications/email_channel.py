"""Email (SMTP) notification channel."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from .base import NotificationChannel, NotificationLevel

logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """Send notifications via SMTP email."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: list[str],
        use_tls: bool = True,
        timeout: int = 15,
    ):
        self._host = smtp_host
        self._port = smtp_port
        self._user = username
        self._password = password
        self._from = from_addr
        self._to = list(to_addrs)
        self._use_tls = use_tls
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "email"

    def send(self, message: str, level: NotificationLevel = NotificationLevel.INFO, **kwargs) -> bool:
        subject = kwargs.get("subject", f"🦀 FinClaw Alert [{level.value.upper()}]")
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = ", ".join(self._to)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as server:
                if self._use_tls:
                    server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._from, self._to, msg.as_string())
            return True
        except Exception as e:
            logger.error("Email send error: %s", e)
            return False
