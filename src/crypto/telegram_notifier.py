"""
FinClaw Crypto Telegram Notifier
=================================
Lightweight Telegram notification system for live trading.
Uses only stdlib (urllib) — no external dependencies.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("finclaw.crypto.telegram")


class TelegramNotifier:
    """Send trading notifications via Telegram Bot API."""

    API_BASE = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: str, chat_id: str, timeout: int = 10):
        """
        Args:
            token: Telegram bot token from @BotFather.
            chat_id: Target chat / channel ID.
            timeout: HTTP request timeout in seconds.
        """
        self._token = token
        self._chat_id = str(chat_id)
        self._timeout = timeout
        self._url = self.API_BASE.format(token=self._token)

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def send(self, message: str) -> bool:
        """Send a plain text message via Telegram bot.

        Returns True on success, False on failure (never raises).
        """
        payload = json.dumps({
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "HTML",
        }).encode("utf-8")

        req = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status == 200:
                    return True
                logger.warning("Telegram API returned %d", resp.status)
                return False
        except urllib.error.HTTPError as exc:
            logger.error("Telegram HTTP error %d: %s", exc.code, exc.reason)
            return False
        except Exception as exc:
            logger.error("Telegram send failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Formatted notifications
    # ------------------------------------------------------------------

    def notify_trade(
        self,
        action: str,
        symbol: str,
        price: float,
        qty: float,
        score: Optional[float] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None,
    ) -> bool:
        """Format and send a trade notification.

        Args:
            action: 'BUY' or 'SELL'.
            symbol: Trading pair e.g. 'BTC/USDT'.
            price: Execution price.
            qty: Quantity traded.
            score: Signal score (for BUY).
            pnl: Realised P&L in USDT (for SELL).
            pnl_pct: Realised P&L percentage (for SELL).
        """
        icon = "🟢" if action.upper() == "BUY" else "🔴"
        parts = [f"{icon} {action.upper()} {symbol} @ {price:,.2f} | Qty: {qty:.6g}"]

        if score is not None:
            parts.append(f"Score: {score:.1f}/10")

        if pnl is not None:
            sign = "+" if pnl >= 0 else ""
            pnl_str = f"PnL: {sign}${pnl:,.2f}"
            if pnl_pct is not None:
                pnl_str += f" ({sign}{pnl_pct:.1f}%)"
            parts.append(pnl_str)

        msg = " | ".join(parts)
        return self.send(msg)

    def notify_daily_summary(
        self,
        portfolio_value: float,
        daily_pnl: float,
        open_positions: int,
    ) -> bool:
        """Send a daily P&L summary.

        Args:
            portfolio_value: Current total portfolio value in USDT.
            daily_pnl: Today's realised + unrealised P&L in USDT.
            open_positions: Number of currently open positions.
        """
        sign = "+" if daily_pnl >= 0 else ""
        pct = (daily_pnl / (portfolio_value - daily_pnl)) * 100 if portfolio_value != daily_pnl else 0.0
        msg = (
            f"📊 Daily Summary | Portfolio: ${portfolio_value:,.0f} "
            f"| Today: {sign}${daily_pnl:,.0f} ({sign}{pct:.1f}%) "
            f"| Open: {open_positions} positions"
        )
        return self.send(msg)

    def notify_risk_alert(self, message: str) -> bool:
        """Send a risk management alert."""
        return self.send(f"⚠️ Risk Alert: {message}")

    def notify_emergency_stop(self, reason: str) -> bool:
        """Send an emergency stop notification."""
        return self.send(f"🛑 EMERGENCY STOP: {reason}")

    def notify_startup(self, mode: str, symbols: list[str], exchange: str) -> bool:
        """Send a startup notification."""
        sym_str = ", ".join(symbols) if symbols else "none"
        return self.send(
            f"🚀 FinClaw Live Runner Started\n"
            f"Mode: {mode} | Exchange: {exchange}\n"
            f"Symbols: {sym_str}\n"
            f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )
