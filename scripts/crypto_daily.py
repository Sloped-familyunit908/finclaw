#!/usr/bin/env python3
"""
FinClaw Crypto Daily Script
============================
Daily crypto monitoring:
  - BTC/ETH/SOL RSI signals
  - Arbitrum DeFi yield scanning
  - Generate daily report to docs/crypto-trading/

Usage:
    python scripts/crypto_daily.py
"""

import os
import sys
from datetime import datetime

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crypto.trading_bot import CryptoTradingBot
from src.defi.defi_monitor import DeFiMonitor


SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
REPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "crypto-trading")


def run_daily() -> str:
    """Run the daily crypto monitoring pipeline and return the report text."""
    lines: list[str] = [
        "=" * 60,
        f"FinClaw Crypto Daily Report — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
    ]

    # ── 1. RSI Signals ──────────────────────────────────────────────
    lines.append("📊 RSI Trading Signals")
    lines.append("-" * 40)
    bot = CryptoTradingBot(sandbox=True)
    for symbol in SYMBOLS:
        try:
            sig = bot.get_signal(symbol)
            emoji = {
                "strong_buy": "🟢🟢",
                "buy": "🟢",
                "hold": "⚪",
                "sell": "🔴",
                "strong_sell": "🔴🔴",
            }.get(sig["signal"], "❓")
            lines.append(
                f"  {symbol:<12} RSI={sig['rsi']:>5.1f}  "
                f"Price=${sig['price']:>10,.2f}  "
                f"{emoji} {sig['signal'].upper()} (conf={sig['confidence']:.0%})"
            )
        except Exception as exc:
            lines.append(f"  {symbol:<12} ⚠ Error: {exc}")

    lines.append("")

    # ── 2. DeFi Yields ──────────────────────────────────────────────
    lines.append("🌾 Top DeFi Yields (Arbitrum)")
    lines.append("-" * 40)
    monitor = DeFiMonitor()
    try:
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=1_000_000, min_apy=5.0, limit=10)
        if pools:
            for p in pools:
                lines.append(
                    f"  {p['project']:<18} {p['symbol']:<20} "
                    f"APY={p['apy']:>7.2f}%  TVL=${p['tvl']:>12,.0f}"
                )
        else:
            lines.append("  No qualifying pools found.")
    except Exception as exc:
        lines.append(f"  ⚠ Error fetching DeFi data: {exc}")

    lines.append("")

    # ── 3. Stablecoin Pools ─────────────────────────────────────────
    lines.append("💲 Best Stablecoin Pools (Arbitrum)")
    lines.append("-" * 40)
    try:
        stables = monitor.find_best_stable_pools(chain="Arbitrum", limit=5)
        if stables:
            for p in stables:
                lines.append(
                    f"  {p['project']:<18} {p['symbol']:<20} "
                    f"APY={p['apy']:>7.2f}%  TVL=${p['tvl']:>12,.0f}"
                )
        else:
            lines.append("  No qualifying stablecoin pools found.")
    except Exception as exc:
        lines.append(f"  ⚠ Error: {exc}")

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    report = run_daily()
    print(report)

    # Save to docs/crypto-trading/
    os.makedirs(REPORT_DIR, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filepath = os.path.join(REPORT_DIR, f"daily-{date_str}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"```\n{report}\n```\n")
    print(f"\n✓ Report saved to {filepath}")


if __name__ == "__main__":
    main()
