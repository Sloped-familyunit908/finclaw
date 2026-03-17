"""
FinClaw Telegram Bot
====================
Lightweight Telegram bot using pure HTTP (no heavy dependencies).
Supports: /quote, /analyze, /alert commands.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

import aiohttp

from src.telegram_bot.alert_manager import AlertManager

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


class TelegramBot:
    """Minimal Telegram bot using long-polling and aiohttp."""

    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        self.base_url = TELEGRAM_API.format(token=self.token)
        self.offset = 0
        self.alert_manager = AlertManager(self)
        self._running = False
        self._handlers: dict[str, Any] = {
            "/start": self._cmd_start,
            "/help": self._cmd_help,
            "/quote": self._cmd_quote,
            "/analyze": self._cmd_analyze,
            "/alert": self._cmd_alert,
            "/alerts": self._cmd_alerts,
        }

    # ── HTTP helpers ──────────────────────────────────────────

    async def _request(self, method: str, **params) -> dict:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{method}"
            async with session.post(url, json=params) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    logger.error("Telegram API error: %s", data)
                return data

    async def send_message(self, chat_id: int | str, text: str, parse_mode: str = "Markdown") -> dict:
        return await self._request("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)

    async def get_updates(self, timeout: int = 30) -> list[dict]:
        data = await self._request("getUpdates", offset=self.offset, timeout=timeout)
        return data.get("result", [])

    # ── Command handlers ──────────────────────────────────────

    async def _cmd_start(self, chat_id: int, args: str):
        await self.send_message(chat_id, (
            "🦀 *FinClaw Bot*\n\n"
            "Commands:\n"
            "/quote AAPL — Get stock quote\n"
            "/analyze TSLA — Technical analysis\n"
            "/alert AAPL > 200 — Set price alert\n"
            "/alerts — List active alerts\n"
            "/help — Show this message"
        ))

    async def _cmd_help(self, chat_id: int, args: str):
        await self._cmd_start(chat_id, args)

    async def _cmd_quote(self, chat_id: int, args: str):
        symbols = args.strip().upper().split()
        if not symbols:
            await self.send_message(chat_id, "Usage: /quote AAPL TSLA MSFT")
            return

        lines = ["📊 *Quotes*\n"]
        lines.append("`{:<8} {:>10} {:>8} {:>8}`".format("Symbol", "Price", "Chg", "%"))
        lines.append("`" + "─" * 38 + "`")

        for sym in symbols[:10]:  # max 10
            try:
                import yfinance as yf
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if hist.empty:
                    lines.append(f"`{sym:<8} {'N/A':>10}`")
                    continue
                price = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
                chg = price - prev
                pct = chg / prev * 100 if prev else 0
                icon = "🟢" if chg >= 0 else "🔴"
                lines.append(f"`{sym:<8} {price:>10.2f} {chg:>+8.2f} {pct:>+7.2f}%` {icon}")
            except Exception as e:
                lines.append(f"`{sym:<8} Error: {str(e)[:20]}`")

        await self.send_message(chat_id, "\n".join(lines))

    async def _cmd_analyze(self, chat_id: int, args: str):
        symbol = args.strip().upper().split()[0] if args.strip() else ""
        if not symbol:
            await self.send_message(chat_id, "Usage: /analyze AAPL")
            return

        try:
            import yfinance as yf
            import numpy as np
            from src.ta import rsi as calc_rsi, macd as calc_macd, sma

            hist = yf.Ticker(symbol).history(period="1y")
            if hist.empty:
                await self.send_message(chat_id, f"No data for {symbol}")
                return

            close = np.array(hist["Close"].tolist(), dtype=np.float64)
            price = close[-1]
            rsi_val = calc_rsi(close, 14)[-1]
            macd_line, signal, histogram = calc_macd(close)
            sma20 = sma(close, 20)[-1]
            sma50 = sma(close, 50)[-1]

            rsi_sig = "OVERSOLD 🟢" if rsi_val < 30 else "OVERBOUGHT 🔴" if rsi_val > 70 else "NEUTRAL ⚪"
            macd_sig = "BULLISH 🟢" if histogram[-1] > 0 else "BEARISH 🔴"
            trend = "UPTREND 📈" if sma20 > sma50 else "DOWNTREND 📉"

            text = (
                f"📊 *{symbol} Analysis*\n\n"
                f"Price: `${price:.2f}`\n"
                f"RSI(14): `{rsi_val:.1f}` — {rsi_sig}\n"
                f"MACD: `{macd_line[-1]:.2f}` — {macd_sig}\n"
                f"SMA20: `{sma20:.2f}` | SMA50: `{sma50:.2f}`\n"
                f"Trend: {trend}\n"
                f"52w High: `{max(close):.2f}` | Low: `{min(close):.2f}`"
            )
            await self.send_message(chat_id, text)
        except Exception as e:
            await self.send_message(chat_id, f"Error analyzing {symbol}: {e}")

    async def _cmd_alert(self, chat_id: int, args: str):
        """Parse: /alert AAPL > 200 or /alert TSLA < 150"""
        parts = args.strip().split()
        if len(parts) < 3:
            await self.send_message(chat_id, "Usage: /alert AAPL > 200\nor: /alert TSLA < 150")
            return

        symbol = parts[0].upper()
        operator = parts[1]
        try:
            threshold = float(parts[2])
        except ValueError:
            await self.send_message(chat_id, "Invalid price. Usage: /alert AAPL > 200")
            return

        if operator not in (">", "<", ">=", "<="):
            await self.send_message(chat_id, "Operator must be >, <, >=, or <=")
            return

        alert_id = self.alert_manager.add_alert(
            chat_id=chat_id,
            symbol=symbol,
            operator=operator,
            threshold=threshold,
        )
        await self.send_message(chat_id, f"✅ Alert #{alert_id}: {symbol} {operator} {threshold}")

    async def _cmd_alerts(self, chat_id: int, args: str):
        alerts = self.alert_manager.get_alerts(chat_id)
        if not alerts:
            await self.send_message(chat_id, "No active alerts.")
            return
        lines = ["🔔 *Active Alerts*\n"]
        for a in alerts:
            lines.append(f"#{a['id']}: {a['symbol']} {a['operator']} {a['threshold']}")
        await self.send_message(chat_id, "\n".join(lines))

    # ── Main loop ─────────────────────────────────────────────

    async def _process_update(self, update: dict):
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id or not text:
            return

        # Parse command
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]  # handle /quote@BotName
        args = parts[1] if len(parts) > 1 else ""

        handler = self._handlers.get(cmd)
        if handler:
            try:
                await handler(chat_id, args)
            except Exception as e:
                logger.exception("Error handling %s: %s", cmd, e)
                await self.send_message(chat_id, f"Error: {e}")

    async def run(self):
        """Start long-polling loop."""
        logger.info("FinClaw Telegram Bot started")
        self._running = True

        # Start alert checker in background
        alert_task = asyncio.create_task(self.alert_manager.check_loop())

        try:
            while self._running:
                try:
                    updates = await self.get_updates(timeout=30)
                    for update in updates:
                        self.offset = update["update_id"] + 1
                        await self._process_update(update)
                except aiohttp.ClientError as e:
                    logger.error("Network error: %s", e)
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.exception("Unexpected error: %s", e)
                    await asyncio.sleep(5)
        finally:
            self._running = False
            alert_task.cancel()

    def stop(self):
        self._running = False


def main():
    """Entry point for telegram bot."""
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable")
        sys.exit(1)
    bot = TelegramBot(token)
    asyncio.run(bot.run())


if __name__ == "__main__":
    main()
