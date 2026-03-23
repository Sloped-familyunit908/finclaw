#!/usr/bin/env python3
"""
FinClaw Live Crypto Trading CLI
=================================

Entry point for running the live/dry-run crypto trading runner.

Usage:
  # Dry-run mode (default, safe — fetches real prices, simulates trades)
  python scripts/live_crypto.py --symbols BTC/USDT ETH/USDT SOL/USDT

  # With Telegram notifications
  python scripts/live_crypto.py --symbols BTC/USDT ETH/USDT \\
      --telegram-token BOT_TOKEN --telegram-chat CHAT_ID

  # Live mode (real money — requires API keys)
  python scripts/live_crypto.py --mode live --exchange binance \\
      --api-key KEY --api-secret SECRET --symbols BTC/USDT
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Ensure project root is on path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.crypto.live_runner import CryptoLiveRunner


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="FinClaw Crypto Live Trading Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Core settings
    parser.add_argument(
        "--mode",
        choices=["dry_run", "live"],
        default="dry_run",
        help="Trading mode (default: dry_run)",
    )
    parser.add_argument(
        "--exchange",
        default="binance",
        help="Exchange ID for ccxt (default: binance)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USDT"],
        help="Trading pairs (default: BTC/USDT)",
    )

    # API keys (live mode)
    parser.add_argument("--api-key", default=None, help="Exchange API key (live mode)")
    parser.add_argument("--api-secret", default=None, help="Exchange API secret (live mode)")

    # Telegram
    parser.add_argument("--telegram-token", default=None, help="Telegram bot token")
    parser.add_argument("--telegram-chat", default=None, help="Telegram chat ID")

    # Trading params
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Signal check interval in minutes (default: 60)",
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=10_000.0,
        help="Initial virtual balance for dry-run (default: 10000)",
    )

    # Risk management
    parser.add_argument(
        "--max-position-pct",
        type=float,
        default=10.0,
        help="Max single position size as %% of portfolio (default: 10)",
    )
    parser.add_argument(
        "--max-exposure-pct",
        type=float,
        default=50.0,
        help="Max total exposure as %% of portfolio (default: 50)",
    )
    parser.add_argument(
        "--daily-loss-limit",
        type=float,
        default=-5.0,
        help="Daily loss limit %% to stop trading (default: -5)",
    )

    # Paths
    parser.add_argument(
        "--dna-path",
        default="evolution_results/best_ever.json",
        help="Path to DNA file (default: evolution_results/best_ever.json)",
    )

    # Logging
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Safety check: live mode requires API keys
    if args.mode == "live":
        if not args.api_key or not args.api_secret:
            print("❌ Live mode requires --api-key and --api-secret")
            sys.exit(1)
        print("⚠️  LIVE MODE — Real money will be used!")
        print(f"   Exchange: {args.exchange}")
        print(f"   Symbols:  {', '.join(args.symbols)}")
        confirm = input("   Type 'CONFIRM' to proceed: ")
        if confirm.strip() != "CONFIRM":
            print("Aborted.")
            sys.exit(0)
    else:
        print(f"🧪 DRY-RUN MODE — No real orders will be placed")
        print(f"   Exchange:  {args.exchange}")
        print(f"   Symbols:   {', '.join(args.symbols)}")
        print(f"   Balance:   ${args.initial_balance:,.0f}")
        print(f"   Interval:  {args.interval}m")
        print()

    runner = CryptoLiveRunner(
        exchange=args.exchange,
        mode=args.mode,
        api_key=args.api_key,
        api_secret=args.api_secret,
        symbols=args.symbols,
        telegram_token=args.telegram_token,
        telegram_chat_id=args.telegram_chat,
        initial_balance=args.initial_balance,
        interval_minutes=args.interval,
        max_position_size_pct=args.max_position_pct,
        max_exposure_pct=args.max_exposure_pct,
        daily_loss_limit_pct=args.daily_loss_limit,
        dna_path=args.dna_path,
        project_root=_project_root,
    )

    try:
        runner.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        runner.stop()


if __name__ == "__main__":
    main()
