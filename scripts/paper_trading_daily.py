#!/usr/bin/env python3
"""
Paper Trading Daily Script

Automated daily pipeline for finclaw paper trading:
1. Load current portfolios
2. Fetch latest prices (US via Yahoo Finance, CN via cn_scanner)
3. Execute strategy signals
4. Update positions and snapshots
5. Generate daily report + summary

Usage:
    python scripts/paper_trading_daily.py          # Run daily pipeline
    python scripts/paper_trading_daily.py --init   # Initialize portfolios
"""

import argparse
import json
import os
import sys
from datetime import date, datetime
from typing import Optional

# Ensure project root on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.paper_report.portfolio_manager import PortfolioManager


def fetch_us_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest US stock prices via Yahoo Finance.

    Returns dict of ticker -> price. Silently skips failures.
    """
    prices = {}
    try:
        import yfinance as yf
        import logging
        import warnings

        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    hist = stock.history(period="5d")
                    if hist is not None and not hist.empty:
                        prices[ticker] = float(hist["Close"].iloc[-1])
                except Exception:
                    pass
    except ImportError:
        pass  # yfinance not installed — return empty
    return prices


def fetch_cn_signals(top: int = 30, min_score: int = 6) -> list[dict]:
    """Fetch A-share scanner signals.

    Returns list of signal dicts with ticker, score, etc.
    Silently returns empty list on failure.
    """
    try:
        from src.cn_scanner import scan_cn_stocks
        results = scan_cn_stocks(top=top, min_score=min_score)
        return results or []
    except Exception:
        return []


def update_portfolio_prices(manager: PortfolioManager, market: str, prices: dict) -> None:
    """Update current prices in portfolio positions."""
    portfolio = manager.load_portfolio(market)
    if portfolio is None:
        return

    for position in portfolio.get("positions", []):
        ticker = position.get("ticker", "")
        if ticker in prices:
            position["current_price"] = prices[ticker]

    manager.save_portfolio(market, portfolio)


def daily_run(
    manager: PortfolioManager,
    report_date: Optional[str] = None,
    skip_fetch: bool = False,
) -> str:
    """Execute the full daily pipeline.

    Args:
        manager: PortfolioManager instance
        report_date: Date string (YYYY-MM-DD), defaults to today
        skip_fetch: If True, skip fetching live market data

    Returns:
        Path to generated daily report
    """
    if report_date is None:
        report_date = date.today().isoformat()

    print(f"  📊 Paper Trading Daily Run: {report_date}")

    # 1. Load portfolios
    us = manager.load_portfolio("US")
    cn = manager.load_portfolio("CN")

    if us is None and cn is None:
        print("  ❌ No portfolios found. Run with --init first.")
        return ""

    # 2. Fetch prices (if not skipped)
    if not skip_fetch:
        # US prices
        if us and us.get("positions"):
            us_tickers = [p["ticker"] for p in us["positions"]]
            print(f"  Fetching US prices for {len(us_tickers)} positions...")
            us_prices = fetch_us_prices(us_tickers)
            if us_prices:
                update_portfolio_prices(manager, "US", us_prices)
                us = manager.load_portfolio("US")
                print(f"  ✅ Updated {len(us_prices)} US prices")
            else:
                print("  ⚠️ No US prices fetched (market closed or network issue)")

        # CN signals
        if cn:
            print("  Fetching CN scanner signals...")
            cn_signals = fetch_cn_signals()
            if cn_signals:
                print(f"  ✅ Got {len(cn_signals)} CN signals")
            else:
                print("  ⚠️ No CN signals (possible non-trading day)")
    else:
        print("  ⏭️ Skipping market data fetch")

    # 3. Add daily snapshots
    if us:
        manager.add_daily_snapshot(us, report_date)
        manager.save_portfolio("US", us)

    if cn:
        manager.add_daily_snapshot(cn, report_date)
        manager.save_portfolio("CN", cn)

    # 4. Generate daily report
    report = manager.generate_daily_report(report_date)
    print(f"  ✅ Daily report generated: reports/{report_date}.md")

    # 5. Update summary
    manager.generate_summary()
    print(f"  ✅ Summary updated: summary.md")

    return report


def main():
    parser = argparse.ArgumentParser(description="FinClaw Paper Trading Daily Pipeline")
    parser.add_argument("--init", action="store_true", help="Initialize portfolios")
    parser.add_argument("--date", default=None, help="Report date (YYYY-MM-DD)")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip fetching market data")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Override data directory (default: docs/paper-trading/)",
    )
    args = parser.parse_args()

    manager = PortfolioManager(data_dir=args.data_dir)

    if args.init:
        result = manager.init_portfolios()
        print("  ✅ Portfolios initialized!")
        print(f"  US: ${result['us']['initial_capital']:,.0f}")
        print(f"  CN: ¥{result['cn']['initial_capital']:,.0f}")
        print(f"  Data dir: {manager.data_dir}")
        return 0

    daily_run(manager, report_date=args.date, skip_fetch=args.skip_fetch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
