"""
FinClaw Telegram Bot
=====================
Zero-install stock analysis. Users just send messages to the bot.

Commands:
  /start           - Welcome + quick guide
  /scan us soros   - Scan market with strategy
  /bt NVDA         - Backtest a stock
  /macro           - Current macro environment
  /help            - List all commands
  
  Also responds to natural language:
  "what should I buy?" -> /scan us buffett
  "how's NVDA doing?" -> /bt NVDA
  "market outlook?" -> /macro

Setup:
  1. Create bot via @BotFather on Telegram
  2. Set TELEGRAM_BOT_TOKEN env var
  3. python telegram_bot.py
"""
import asyncio
import os
import sys
import json
import logging
import warnings

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server import handle_scan, handle_backtest, handle_macro, handle_info

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False


# ═══ Message Formatters ═══

def format_scan_result(results):
    """Format scan results for Telegram."""
    if not results:
        return "No stocks matched the criteria."

    lines = []
    for r in results:
        lines.append(f"📊 *{r['market'].upper()} — {r['strategy'].upper()}*")
        lines.append(f"Portfolio: *{r['total_return']:+.1f}%* ({r['annual_return']:+.1f}%/year)")
        lines.append(f"P&L: ${r['pnl']:+,}")
        lines.append("")
        for h in r["holdings"][:8]:
            emoji = "🟢" if h["return"] > 0 else "🔴"
            lines.append(f"{emoji} `{h['ticker']:<10}` {h['name']:<15} {h['return']:+.1f}% (${h['pnl']:+,})")
        lines.append("")
    lines.append("_Not financial advice. Past performance ≠ future results._")
    return "\n".join(lines)


def format_backtest_result(r):
    """Format backtest result for Telegram."""
    if "error" in r:
        return f"❌ {r['error']}"

    emoji = "🟢" if r["finclaw_return"] > 0 else "🔴"
    alpha_emoji = "📈" if r["alpha"] > 0 else "📉"

    return (
        f"{emoji} *{r['ticker']}* ({r['period']})\n\n"
        f"Buy & Hold: {r['buy_and_hold']:+.1f}%\n"
        f"FinClaw: *{r['finclaw_return']:+.1f}%* ({r['annual_return']:+.1f}%/year)\n"
        f"{alpha_emoji} Alpha: {r['alpha']:+.1f}%\n"
        f"Max Drawdown: {r['max_drawdown']:.1f}%\n"
        f"Trades: {r['total_trades']} | Win Rate: {r['win_rate']}%\n\n"
        f"_Not financial advice._"
    )


def format_macro_result(r):
    """Format macro analysis for Telegram."""
    regime_emoji = {"RISK_ON": "🟢", "RISK_OFF": "🔴", "MIXED": "🟡"}.get(r["overall_regime"], "⚪")

    lines = [
        f"{regime_emoji} *Market Regime: {r['overall_regime']}*\n",
        f"🎯 VIX: {r['sentiment']['vix']} ({r['sentiment']['vix_regime']})",
        f"📊 10Y Yield: {r['monetary']['us_10y_yield']}%",
        f"💰 Bitcoin: {r['sentiment']['bitcoin']}",
        f"🛢️ Oil: {r['commodities']['oil']}",
        f"🥇 Gold: {r['commodities']['gold']}",
        f"🔧 Copper: {r['commodities']['copper']}",
        f"📈 Economy: {r['economy']['phase']}",
        f"🌊 K-Wave: {r['kondratieff']['season']}",
        "",
        "*Favored Sectors:*",
    ]
    for s in r.get("favored_sectors", [])[:5]:
        lines.append(f"  🟢 {s['sector']} ({s['adjustment']:+.3f})")

    if r.get("avoided_sectors"):
        lines.append("\n*Avoid:*")
        for s in r["avoided_sectors"][:3]:
            lines.append(f"  🔴 {s['sector']} ({s['adjustment']:+.3f})")

    return "\n".join(lines)


def format_help():
    """Format help message."""
    return (
        "🐋 *FinClaw — AI Financial Intelligence*\n\n"
        "*Commands:*\n"
        "/scan `market` `strategy` — Scan stocks\n"
        "/bt `TICKER` — Backtest a stock\n"
        "/macro — Market environment\n"
        "/strategies — List strategies\n"
        "/help — This message\n\n"
        "*Markets:* us, china, hk, japan, korea, all\n"
        "*Strategies:* soros, buffett, druckenmiller, lynch, dalio, conservative\n\n"
        "*Examples:*\n"
        "`/scan us soros` — US stocks, Soros strategy\n"
        "`/scan china buffett` — A-shares, Buffett style\n"
        "`/bt NVDA` — Backtest NVIDIA\n"
        "`/bt 600519.SS` — Backtest Moutai\n\n"
        "_Open source: github.com/NeuZhou/finclaw_"
    )


def format_strategies():
    """Format strategies list."""
    info = handle_info()
    lines = ["🐋 *FinClaw Strategies*\n"]
    risk_emojis = {"VERY HIGH": "🔴🔴", "HIGH": "🔴", "MEDIUM-HIGH": "🟡", "MEDIUM": "🟢", "LOW": "🟢🟢"}
    for name, s in info["strategies"].items():
        emoji = risk_emojis.get(s["risk"], "⚪")
        lines.append(f"{emoji} *{name}* ({s['target_annual']}/y)")
        lines.append(f"   {s['description']}\n")
    return "\n".join(lines)


# ═══ Telegram Handlers (only when library available) ═══
if HAS_TELEGRAM:
    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "*Welcome to FinClaw!*\n\nAI-powered stock analysis.\n\n"
            "Try: `/scan us soros` or `/bt NVDA`\nType /help for all commands.",
            parse_mode="Markdown")

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_help(), parse_mode="Markdown")

    async def cmd_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(format_strategies(), parse_mode="Markdown")

    async def cmd_macro(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Analyzing...", parse_mode="Markdown")
        result = handle_macro()
        await update.message.reply_text(format_macro_result(result), parse_mode="Markdown")

    async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args or []
        market = args[0] if len(args) > 0 else "us"
        style = args[1] if len(args) > 1 else "soros"
        await update.message.reply_text(f"Scanning {market.upper()} with {style}...")
        result = await handle_scan(market, style, 100000, "1y")
        await update.message.reply_text(format_scan_result(result), parse_mode="Markdown")

    async def cmd_backtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args or []
        if not args:
            await update.message.reply_text("Usage: /bt TICKER\nExample: /bt NVDA")
            return
        ticker = args[0].upper()
        period = args[1] if len(args) > 1 else "1y"
        await update.message.reply_text(f"Backtesting {ticker}...")
        result = await handle_backtest(ticker, period)
        await update.message.reply_text(format_backtest_result(result), parse_mode="Markdown")

    def run_bot():
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            print("ERROR: Set TELEGRAM_BOT_TOKEN environment variable")
            sys.exit(1)
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CommandHandler("strategies", cmd_strategies))
        app.add_handler(CommandHandler("macro", cmd_macro))
        app.add_handler(CommandHandler("scan", cmd_scan))
        app.add_handler(CommandHandler("bt", cmd_backtest))
        print("FinClaw Telegram Bot started!")
        app.run_polling()


if __name__ == "__main__":
    # Demo mode (works without telegram library)
    async def demo():
        print("=== MACRO ===")
        r = handle_macro()
        print(format_macro_result(r))
        print()
        print("=== STRATEGIES ===")
        print(format_strategies())
        print()
        print("=== BACKTEST NVDA ===")
        r = await handle_backtest("NVDA", "1y")
        print(format_backtest_result(r))
        print()
        print("=== SCAN US SOROS ===")
        r = await handle_scan("us", "druckenmiller", 100000, "1y")
        print(format_scan_result(r))

    asyncio.run(demo())
