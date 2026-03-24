#!/usr/bin/env python3
"""
FinClaw Crypto Paper Trading Launcher
======================================
Starts the crypto paper trading bot in dry-run mode.
Uses the latest evolved DNA from evolution_results_crypto/best_ever.json.

Usage:
    python scripts/start_paper_trading.py
    python scripts/start_paper_trading.py --symbols BTC/USDT ETH/USDT SOL/USDT
    python scripts/start_paper_trading.py --interval 30  # 30 minutes between cycles

Safety:
    - Always dry-run mode (no real orders)
    - Daily loss limit: -5%
    - Max single position: 10% of portfolio
    - Max total exposure: 50%
    - Emergency stop: create STOP_TRADING file

Reporting:
    - Trades logged to data/crypto/paper_trades.json
    - Daily P&L summary to docs/paper-trading/crypto-daily.json
    - Feishu notification on significant events
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.crypto.live_runner import CryptoLiveRunner


# Top coins that we have data for
DEFAULT_SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
    "XRP/USDT", "ADA/USDT", "DOGE/USDT", "AVAX/USDT",
    "DOT/USDT", "LINK/USDT", "LTC/USDT", "UNI/USDT",
    "ATOM/USDT", "FIL/USDT", "ARB/USDT", "OP/USDT", "APT/USDT",
]

CRYPTO_DNA_PATH = "evolution_results_crypto/best_ever.json"
TRADE_LOG_PATH = "data/crypto/paper_trades.json"
DAILY_SUMMARY_PATH = "docs/paper-trading/crypto-daily.json"


def setup_logging():
    """Configure logging for paper trading."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"paper_trading_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("finclaw.paper_trading")


def load_crypto_dna(path: Path) -> dict:
    """Load the latest crypto evolution DNA."""
    if not path.exists():
        print(f"WARNING: Crypto DNA not found at {path}")
        print("Using default parameters")
        return {}

    with open(path) as f:
        data = json.load(f)

    dna = data.get("dna", data)
    gen = data.get("generation", "?")
    fitness = data.get("fitness", "?")
    print(f"Loaded Crypto DNA: Gen {gen}, Fitness {fitness}")
    return dna


def save_daily_summary(runner: CryptoLiveRunner, summary_path: Path):
    """Save daily P&L summary to JSON for tracking."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing summaries
    summaries = []
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summaries = json.load(f)
        except Exception:
            summaries = []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Check if today's entry already exists
    existing = [s for s in summaries if s.get("date") == today]
    if existing:
        entry = existing[0]
    else:
        entry = {"date": today}
        summaries.append(entry)

    # Update entry
    entry["portfolio_value"] = runner.portfolio_value()
    entry["cash"] = runner.cash
    entry["positions"] = len(runner.positions)
    entry["daily_pnl"] = runner.daily_pnl
    entry["total_trades"] = len(runner.trade_log)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Position details
    entry["holdings"] = {}
    for sym, pos in runner.positions.items():
        entry["holdings"][sym] = {
            "entry_price": pos.entry_price,
            "qty": pos.qty,
            "entry_time": pos.entry_time,
        }

    with open(summary_path, "w") as f:
        json.dump(summaries, f, indent=2)

    return entry


def main():
    parser = argparse.ArgumentParser(description="FinClaw Crypto Paper Trading")
    parser.add_argument(
        "--symbols", nargs="+", default=DEFAULT_SYMBOLS,
        help="Trading symbols (default: top 17 coins)"
    )
    parser.add_argument(
        "--exchange", default="binance",
        help="Exchange to use for price data (default: binance)"
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Minutes between trading cycles (default: 60)"
    )
    parser.add_argument(
        "--balance", type=float, default=10000.0,
        help="Initial virtual balance in USDT (default: 10000)"
    )
    parser.add_argument(
        "--max-positions", type=int, default=5,
        help="Maximum concurrent positions (default: 5)"
    )
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("FinClaw Crypto Paper Trading")
    logger.info("=" * 60)

    # Load DNA
    dna_path = project_root / CRYPTO_DNA_PATH
    crypto_dna = load_crypto_dna(dna_path)

    # Override max_positions from CLI if provided
    if crypto_dna:
        crypto_dna["max_positions"] = args.max_positions

    logger.info(f"Exchange: {args.exchange}")
    logger.info(f"Symbols: {len(args.symbols)} coins")
    logger.info(f"Interval: {args.interval} minutes")
    logger.info(f"Initial balance: ${args.balance:,.2f}")
    logger.info(f"Max positions: {args.max_positions}")
    logger.info(f"Mode: DRY-RUN (paper trading)")

    # Create runner
    runner = CryptoLiveRunner(
        exchange=args.exchange,
        mode="dry_run",
        symbols=args.symbols,
        initial_balance=args.balance,
        interval_minutes=args.interval,
        max_position_size_pct=10.0,
        max_exposure_pct=50.0,
        daily_loss_limit_pct=-5.0,
        dna_path=CRYPTO_DNA_PATH,
        trade_log_path=TRADE_LOG_PATH,
        project_root=str(project_root),
    )

    # Load DNA into runner
    runner.load_dna()
    if crypto_dna:
        runner.dna.update(crypto_dna)

    logger.info("Paper trading started. Press Ctrl+C to stop.")
    logger.info(f"Trade log: {TRADE_LOG_PATH}")
    logger.info(f"Daily summary: {DAILY_SUMMARY_PATH}")
    logger.info(f"Emergency stop: create '{project_root}/STOP_TRADING' file")

    # Save initial summary
    summary_path = project_root / DAILY_SUMMARY_PATH
    save_daily_summary(runner, summary_path)

    # Start the runner
    try:
        runner.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Save final summary
        entry = save_daily_summary(runner, summary_path)
        logger.info(f"Final portfolio value: ${entry.get('portfolio_value', 0):,.2f}")
        logger.info(f"Total trades: {entry.get('total_trades', 0)}")
        logger.info("Paper trading stopped.")


if __name__ == "__main__":
    main()
