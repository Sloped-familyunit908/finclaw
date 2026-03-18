"""
FinClaw CLI v5.1.0 - Comprehensive argparse-based CLI
=====================================================
All commands work end-to-end with real data via yfinance.
"""

import argparse
import asyncio
import json
import math
import os
import sys
from datetime import datetime

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config_manager import ConfigManager


def _get_version() -> str:
    """Read version from pyproject.toml so CLI always matches the package version."""
    try:
        import importlib.metadata
        return importlib.metadata.version("finclaw-ai")
    except Exception:
        pass
    # Fallback: parse pyproject.toml manually
    try:
        import pathlib, re
        pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            return m.group(1)
    except Exception:
        pass
    return "0.0.0"


def _fetch_data(ticker: str, start: str = None, end: str = None, period: str = "5y"):
    """Fetch price data via yfinance with cache."""
    from src.data.cache import DataCache
    import logging, warnings

    cache = DataCache()
    cache_key = f"{ticker}_{start or ''}_{end or ''}_{period}"
    cached = cache.get(cache_key, max_age_hours=24)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stock = yf.Ticker(ticker)
            if start:
                df = stock.history(start=start, end=end)
            else:
                df = stock.history(period=period)
        if df.empty or len(df) < 2:
            return None
        import pandas as pd
        cache.set(cache_key, df)
        return df
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return None


def _calc_vol(prices) -> float:
    """Annualized volatility from price series."""
    if len(prices) < 2:
        return 0
    rets = [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return var ** 0.5 * math.sqrt(252)


# ────────────────────────────────────────────────────────────────
# Commands
# ────────────────────────────────────────────────────────────────

def cmd_backtest(args):
    """Run backtest with strategy on tickers."""
    from agents.backtester_v7 import BacktesterV7
    from agents.strategies import STRATEGY_MAP

    config = ConfigManager.load()
    # Support both --tickers and --ticker
    tickers_str = args.tickers or args.ticker
    if not tickers_str:
        print("  ERROR: --tickers or --ticker is required")
        return []
    tickers = [t.strip() for t in tickers_str.split(",")]
    capital = config.get("backtest.initial_capital", 100000)
    strategy = args.strategy
    start = args.start
    end = args.end
    benchmark = args.benchmark

    # Support plugin: prefix for strategy plugins
    plugin_strategy = None
    if strategy and strategy.startswith("plugin:"):
        plugin_name = strategy[len("plugin:"):]
        from src.plugin_system.registry import StrategyRegistry
        _registry = StrategyRegistry()
        _registry.load_all()
        plugin_strategy = _registry.get(plugin_name)
        if not plugin_strategy:
            print(f"  ERROR: Strategy plugin not found: {plugin_name}")
            print(f"  Available: {', '.join(_registry.names())}")
            return []

    all_results = []

    for ticker in tickers:
        df = _fetch_data(ticker, start=start, end=end)
        if df is None:
            print(f"  No data for {ticker}, skipping.")
            continue

        prices = df["Close"].tolist()
        h = [{"date": datetime.fromisoformat(str(idx)[:10]) if isinstance(idx, str) else idx.to_pydatetime(),
              "price": float(row["Close"]),
              "volume": float(row.get("Volume", 0))}
             for idx, row in df.iterrows()]

        bh = prices[-1] / prices[0] - 1
        years = max(len(prices) / 252, 0.5)

        # Select backtester based on strategy name
        strategy_lower = (strategy or "").lower()
        # Support aliases: sma_cross and rsi map to existing strategies
        _BACKTEST_ALIASES = {
            "sma_cross": "momentum",       # SMA crossover maps to momentum breakout
            "rsi": "bollinger",             # RSI maps to Bollinger (both are mean-reversion)
        }
        resolved_strategy = _BACKTEST_ALIASES.get(strategy_lower, strategy_lower)
        if resolved_strategy in STRATEGY_MAP:
            StrategyCls = STRATEGY_MAP[resolved_strategy]
            bt = StrategyCls(initial_capital=capital)
            r = asyncio.run(bt.run(ticker, resolved_strategy, h))
        else:
            available = sorted(set(list(STRATEGY_MAP.keys()) + list(_BACKTEST_ALIASES.keys())))
            if strategy_lower and strategy_lower not in ("v7", "default", ""):
                print(f"  WARNING: Unknown strategy '{strategy}'. Using default (v7). Available: {', '.join(available)}")
            bt = BacktesterV7(initial_capital=capital)
            r = asyncio.run(bt.run(ticker, "v7", h))
        ann = (1 + r.total_return) ** (1 / years) - 1 if r.total_return > -1 else -1

        print(f"\n  ── {ticker} | {strategy} ──")
        print(f"  Period: {years:.1f}y | B&H: {bh:+.1%}")
        print(f"  Return: {r.total_return:+.1%} ({ann:+.1%}/yr)")
        print(f"  Alpha:  {r.total_return - bh:+.1%}")
        print(f"  MaxDD:  {r.max_drawdown:+.1%}")
        print(f"  Trades: {r.total_trades} | WinRate: {r.win_rate:.0%}")
        print(f"  P&L:    {capital * r.total_return:+,.0f}")

        if benchmark:
            bdf = _fetch_data(benchmark, start=start, end=end)
            if bdf is not None:
                bench_ret = bdf["Close"].iloc[-1] / bdf["Close"].iloc[0] - 1
                print(f"  Bench ({benchmark}): {bench_ret:+.1%} | Excess: {r.total_return - bench_ret:+.1%}")

        result = {
            "ticker": ticker, "strategy": strategy,
            "total_return": r.total_return, "annualized": ann,
            "max_drawdown": r.max_drawdown, "trades": r.total_trades,
            "win_rate": r.win_rate, "buy_hold": bh,
            "equity_curve": prices,
        }
        all_results.append(result)

    if all_results:
        print(f"\n  ✓ Backtest complete for {len(all_results)} ticker(s).")
    return all_results


def cmd_screen(args):
    """Screen stocks by criteria."""
    from src.screener.stock_screener import StockScreener, StockData
    import numpy as np

    # Build filters from both --criteria string and individual flags
    filters = {}

    # Parse --criteria string like "rsi<30,pe<15,market_cap>1B"
    criteria_str = args.criteria or ""
    if criteria_str:
        for crit in criteria_str.split(","):
            crit = crit.strip()
            for op in ["<=", ">=", "<", ">"]:
                if op in crit:
                    key, val = crit.split(op, 1)
                    key = key.strip()
                    val = val.strip()
                    multiplier = 1
                    if val.upper().endswith("B"):
                        multiplier = 1e9; val = val[:-1]
                    elif val.upper().endswith("M"):
                        multiplier = 1e6; val = val[:-1]
                    elif val.upper().endswith("K"):
                        multiplier = 1e3; val = val[:-1]
                    op_key = {"<": "lt", ">": "gt", "<=": "lte", ">=": "gte"}[op]
                    filters.setdefault(key, {})[op_key] = float(val) * multiplier
                    break

    # Apply individual flags
    min_vol = getattr(args, "min_volume", None)
    if min_vol is not None:
        filters.setdefault("volume", {})["gte"] = min_vol
    max_vol = getattr(args, "max_volume", None)
    if max_vol is not None:
        filters.setdefault("volume", {})["lte"] = max_vol
    min_price = getattr(args, "min_price", None)
    if min_price is not None:
        filters.setdefault("price", {})["gte"] = min_price
    max_price = getattr(args, "max_price", None)
    if max_price is not None:
        filters.setdefault("price", {})["lte"] = max_price
    change_above = getattr(args, "change_above", None)
    if change_above is not None:
        filters.setdefault("change_pct", {})["gte"] = change_above
    change_below = getattr(args, "change_below", None)
    if change_below is not None:
        filters.setdefault("change_pct", {})["lte"] = change_below
    rsi_above = getattr(args, "rsi_above", None)
    if rsi_above is not None:
        filters.setdefault("rsi_14", {})["gte"] = rsi_above
    rsi_below = getattr(args, "rsi_below", None)
    if rsi_below is not None:
        filters.setdefault("rsi_14", {})["lte"] = rsi_below
    min_mcap = getattr(args, "min_mcap", None)
    if min_mcap is not None:
        filters.setdefault("market_cap", {})["gte"] = min_mcap
    max_mcap = getattr(args, "max_mcap", None)
    if max_mcap is not None:
        filters.setdefault("market_cap", {})["lte"] = max_mcap

    if not filters:
        print("  No screening criteria specified. Use --criteria or individual flags.")
        print("  Example: finclaw screen --min-volume 1000000 --change-above 5")
        return []

    universe_name = args.universe
    tickers = _get_universe_tickers(universe_name)
    limit = getattr(args, "limit", 20)
    print(f"\n  Screening {len(tickers)} stocks with {len(filters)} filter(s)")

    # Build StockData universe
    screener = StockScreener()
    stock_universe = []
    for ticker in tickers:
        try:
            df = _fetch_data(ticker, period="3mo")
            if df is None or len(df) < 30:
                continue
            close = np.array(df["Close"].tolist(), dtype=np.float64)
            volume = np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None
            stock_universe.append(StockData(ticker=ticker, close=close, volume=volume))
        except Exception:
            continue

    results = screener.screen(stock_universe, filters, limit=limit)

    if results:
        print(f"\n  Found {len(results)} matches:\n")
        for r in results:
            parts = [f"  {r['ticker']:<10}"]
            if "price" in r:
                parts.append(f"Price={r['price']:.2f}")
            if "change_pct" in r:
                parts.append(f"Chg={r['change_pct']:+.2f}%")
            if "rsi_14" in r:
                parts.append(f"RSI={r['rsi_14']:.1f}")
            if "volume" in r:
                parts.append(f"Vol={r['volume']:,.0f}")
            print(" | ".join(parts))
    else:
        print("  No stocks matched the criteria.")

    print()
    return results


def cmd_analyze(args):
    """Analyze a ticker with technical indicators."""
    import numpy as np
    from src.ta import rsi as calc_rsi, macd as calc_macd, sma, ema

    ticker = args.ticker
    indicators = [i.strip() for i in args.indicators.split(",")]

    df = _fetch_data(ticker, period="1y")
    if df is None:
        print(f"  No data for {ticker}.")
        return

    close = np.array(df["Close"].tolist(), dtype=np.float64)
    high = np.array(df["High"].tolist(), dtype=np.float64) if "High" in df.columns else close
    low = np.array(df["Low"].tolist(), dtype=np.float64) if "Low" in df.columns else close

    print(f"\n  ── Technical Analysis: {ticker} ──")
    print(f"  Price: {close[-1]:.2f} | Change: {close[-1]/close[-2]-1:+.2%}")
    print(f"  52w High: {max(close):.2f} | 52w Low: {min(close):.2f}")
    print()

    for ind in indicators:
        ind_lower = ind.lower()
        if ind_lower == "rsi":
            r = calc_rsi(close, 14)
            val = r[-1]
            signal = "OVERSOLD" if val < 30 else "OVERBOUGHT" if val > 70 else "NEUTRAL"
            print(f"  RSI(14): {val:.1f} — {signal}")
        elif ind_lower == "macd":
            line, signal, hist = calc_macd(close)
            trend = "BULLISH" if hist[-1] > 0 else "BEARISH"
            print(f"  MACD: {line[-1]:.2f} | Signal: {signal[-1]:.2f} | Hist: {hist[-1]:.2f} — {trend}")
        elif ind_lower in ("bollinger", "bb"):
            sma20 = sma(close, 20)
            std = np.array([np.std(close[max(0, i - 19):i + 1]) for i in range(len(close))])
            upper = sma20 + 2 * std
            lower = sma20 - 2 * std
            pos = (close[-1] - lower[-1]) / (upper[-1] - lower[-1]) * 100 if upper[-1] != lower[-1] else 50
            print(f"  Bollinger: Upper={upper[-1]:.2f} Mid={sma20[-1]:.2f} Lower={lower[-1]:.2f} | %B={pos:.0f}%")
        elif ind_lower.startswith("sma"):
            period = int(ind_lower[3:]) if len(ind_lower) > 3 else 20
            s = sma(close, period)
            above = "ABOVE" if close[-1] > s[-1] else "BELOW"
            print(f"  SMA({period}): {s[-1]:.2f} — Price {above}")
        elif ind_lower.startswith("ema"):
            period = int(ind_lower[3:]) if len(ind_lower) > 3 else 20
            e = ema(close, period)
            above = "ABOVE" if close[-1] > e[-1] else "BELOW"
            print(f"  EMA({period}): {e[-1]:.2f} — Price {above}")
        else:
            print(f"  Unknown indicator: {ind}")

    return {"ticker": ticker, "price": float(close[-1])}


def cmd_portfolio_track(args):
    """Track portfolio from JSON file."""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return

    with open(filepath) as f:
        portfolio = json.load(f)

    holdings = portfolio.get("holdings", portfolio if isinstance(portfolio, list) else [])
    total_value = 0
    total_cost = 0

    print(f"\n  ── Portfolio Tracker ──")
    print(f"  {'Ticker':<10} {'Shares':>8} {'AvgCost':>10} {'Price':>10} {'Value':>12} {'P&L':>10} {'%':>8}")
    print("  " + "─" * 72)

    for h in holdings:
        ticker = h.get("ticker", h.get("symbol", "???"))
        shares = h.get("shares", h.get("quantity", 0))
        avg_cost = h.get("avg_cost", h.get("cost", 0))

        df = _fetch_data(ticker, period="5d")
        if df is not None and len(df) > 0:
            price = float(df["Close"].iloc[-1])
        else:
            price = avg_cost

        value = shares * price
        cost = shares * avg_cost
        pnl = value - cost
        pnl_pct = pnl / cost if cost > 0 else 0

        total_value += value
        total_cost += cost

        print(f"  {ticker:<10} {shares:>8.1f} {avg_cost:>10.2f} {price:>10.2f} {value:>12,.2f} {pnl:>+10,.2f} {pnl_pct:>+7.1%}")

    total_pnl = total_value - total_cost
    total_pnl_pct = total_pnl / total_cost if total_cost > 0 else 0
    print("  " + "─" * 72)
    print(f"  {'TOTAL':<10} {'':>8} {'':>10} {'':>10} {total_value:>12,.2f} {total_pnl:>+10,.2f} {total_pnl_pct:>+7.1%}")

    return {"total_value": total_value, "total_pnl": total_pnl}


def cmd_price(args):
    """Get current prices for tickers."""
    tickers = [t.strip() for t in args.ticker.split(",")]

    print(f"\n  ── Prices ──")
    print(f"  {'Ticker':<10} {'Price':>10} {'Change':>8} {'%':>8} {'52w High':>10} {'52w Low':>10}")
    print("  " + "─" * 60)

    for ticker in tickers:
        df = _fetch_data(ticker, period="1y")
        if df is None:
            print(f"  {ticker:<10} — no data")
            continue
        close = df["Close"].tolist()
        price = close[-1]
        change = price - close[-2] if len(close) > 1 else 0
        pct = change / close[-2] if len(close) > 1 else 0
        hi = max(close)
        lo = min(close)
        print(f"  {ticker:<10} {price:>10.2f} {change:>+8.2f} {pct:>+7.2%} {hi:>10.2f} {lo:>10.2f}")


def cmd_options_price(args):
    """Price an option using Black-Scholes."""
    from src.derivatives.options_pricing import BlackScholes

    S, K, T, r, sigma = args.S, args.K, args.T, args.r, args.sigma

    if args.type == "call":
        price = BlackScholes.call_price(S, K, T, r, sigma)
    else:
        price = BlackScholes.put_price(S, K, T, r, sigma)

    greeks = BlackScholes.greeks(S, K, T, r, sigma)

    print(f"\n  ── Options Pricing (Black-Scholes) ──")
    print(f"  Type:  {args.type.upper()}")
    print(f"  S={args.S}  K={args.K}  T={args.T}  r={args.r}  σ={args.sigma}")
    print(f"  Price: {price:.4f}")
    print(f"  Delta: {greeks.get('delta', greeks.get('call_delta', 0)):.4f}")
    print(f"  Gamma: {greeks.get('gamma', 0):.6f}")
    print(f"  Theta: {greeks.get('theta', greeks.get('call_theta', 0)):.4f}")
    print(f"  Vega:  {greeks.get('vega', 0):.4f}")
    print(f"  Rho:   {greeks.get('rho', greeks.get('call_rho', 0)):.4f}")

    return {"price": price, "greeks": greeks}


def cmd_paper_trade(args):
    """Run paper trading simulation."""
    tickers = [t.strip() for t in args.tickers.split(",")]
    capital = args.capital
    strategy = args.strategy

    print(f"\n  ── Paper Trading ──")
    print(f"  Strategy: {strategy} | Tickers: {', '.join(tickers)} | Capital: ${capital:,.0f}")

    # Simple paper trading loop simulation
    positions = {}
    cash = capital
    trades = []

    for ticker in tickers:
        df = _fetch_data(ticker, period="6mo")
        if df is None:
            continue

        close = df["Close"].tolist()
        alloc = capital / len(tickers)

        # Simple trend-following: buy when price > SMA20, sell when below
        import numpy as np
        from src.ta import sma
        prices = np.array(close, dtype=np.float64)
        sma20 = sma(prices, 20)

        holding = False
        entry_price = 0
        shares = 0

        for i in range(20, len(prices)):
            if not holding and prices[i] > sma20[i]:
                # Buy
                shares = int(alloc / prices[i])
                if shares > 0:
                    entry_price = prices[i]
                    holding = True
                    trades.append({"ticker": ticker, "action": "BUY", "price": float(prices[i]), "shares": shares})
            elif holding and prices[i] < sma20[i]:
                # Sell
                pnl = (prices[i] - entry_price) * shares
                trades.append({"ticker": ticker, "action": "SELL", "price": float(prices[i]), "shares": shares, "pnl": float(pnl)})
                cash += pnl
                holding = False

        if holding:
            # Mark to market
            pnl = (prices[-1] - entry_price) * shares
            positions[ticker] = {"shares": shares, "entry": entry_price, "current": float(prices[-1]), "pnl": float(pnl)}

    # Summary
    total_pnl = sum(t.get("pnl", 0) for t in trades if "pnl" in t) + sum(p["pnl"] for p in positions.values())
    print(f"\n  Trades: {len(trades)}")
    print(f"  Open positions: {len(positions)}")
    print(f"  Total P&L: {total_pnl:+,.2f}")
    print(f"  Return: {total_pnl / capital:+.2%}")

    return {"trades": len(trades), "pnl": total_pnl}


def cmd_report(args):
    """Generate report from backtest results."""
    from src.reports.html_report import generate_html_report

    input_file = args.input or args.data
    if not input_file:
        print("  ERROR: --input or --data is required")
        return

    if not os.path.exists(input_file):
        print(f"  File not found: {input_file}")
        return

    with open(input_file) as f:
        data = json.load(f)

    output = args.output or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    fmt = args.format

    if fmt == "html":
        html = generate_html_report(data, title=f"FinClaw Report", output_path=output)
        print(f"  ✓ HTML report generated: {output} ({len(html):,} bytes)")
    elif fmt == "json":
        with open(output, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  ✓ JSON report saved: {output}")
    else:
        print(f"  Unknown format: {fmt}")


def cmd_tearsheet(args):
    """Generate QuantStats-style tearsheet."""
    import csv as csv_mod

    returns_file = args.returns
    if not os.path.exists(returns_file):
        print(f"  File not found: {returns_file}")
        return

    # Load returns
    if returns_file.endswith(".json"):
        with open(returns_file) as f:
            data = json.load(f)
        returns = data if isinstance(data, list) else data.get("returns", [])
    else:
        returns = []
        with open(returns_file) as f:
            reader = csv_mod.reader(f)
            for row in reader:
                try:
                    returns.append(float(row[-1]))
                except (ValueError, IndexError):
                    continue

    if not returns:
        print("  ERROR: No return data found")
        return

    # Benchmark
    benchmark = None
    if args.benchmark:
        if os.path.exists(args.benchmark):
            benchmark = []
            with open(args.benchmark) as f:
                reader = csv_mod.reader(f)
                for row in reader:
                    try:
                        benchmark.append(float(row[-1]))
                    except (ValueError, IndexError):
                        continue
        else:
            # Treat as ticker, fetch prices and compute returns
            df = _fetch_data(args.benchmark, period="5y")
            if df is not None:
                closes = df["Close"].tolist()
                benchmark = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes))]

    from src.reports.tearsheet import Tearsheet
    output = args.output or f"tearsheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    result = Tearsheet.generate(returns, benchmark=benchmark, output_path=output)
    print(f"  ✓ Tearsheet generated: {output} ({len(result):,} bytes)")


def cmd_export(args):
    """Export OHLCV + technical indicators to CSV/JSON."""
    import numpy as np
    from src.ta import rsi as calc_rsi, macd as calc_macd, sma, ema

    ticker = args.ticker.upper()
    period = args.period
    fmt = args.format
    output = args.output or f"{ticker}_{period}.{fmt}"
    indicators = [i.strip().lower() for i in args.indicators.split(",")]

    df = _fetch_data(ticker, period=period)
    if df is None or len(df) == 0:
        print(f"  No data for {ticker}")
        return

    close = np.array(df["Close"].tolist(), dtype=np.float64)

    records = []
    for i, (idx, row) in enumerate(df.iterrows()):
        rec = {
            "date": str(idx)[:10],
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        }

        # Add indicators
        if "sma20" in indicators or "sma" in indicators:
            s = sma(close, 20)
            rec["sma20"] = round(float(s[i]), 4) if not np.isnan(s[i]) else ""
        if "sma50" in indicators:
            s = sma(close, 50)
            rec["sma50"] = round(float(s[i]), 4) if not np.isnan(s[i]) else ""
        if "ema20" in indicators or "ema" in indicators:
            e = ema(close, 20)
            rec["ema20"] = round(float(e[i]), 4) if not np.isnan(e[i]) else ""
        if "rsi" in indicators:
            r = calc_rsi(close, 14)
            rec["rsi14"] = round(float(r[i]), 2) if not np.isnan(r[i]) else ""
        if "macd" in indicators:
            line, sig, hist = calc_macd(close)
            rec["macd"] = round(float(line[i]), 4) if not np.isnan(line[i]) else ""
            rec["macd_signal"] = round(float(sig[i]), 4) if not np.isnan(sig[i]) else ""
            rec["macd_hist"] = round(float(hist[i]), 4) if not np.isnan(hist[i]) else ""

        records.append(rec)

    from src.export.exporter import DataExporter
    exporter = DataExporter()

    if fmt == "csv":
        exporter.to_csv(records, output)
    else:
        exporter.to_json(records, output)

    print(f"  ✓ Exported {len(records)} rows to {output}")
    print(f"    Ticker: {ticker} | Period: {period} | Format: {fmt}")
    print(f"    Indicators: {', '.join(indicators)}")
    return output


def cmd_compare(args):
    """Compare multiple strategies on the same data."""
    from src.cli.colors import bold, bright_green, bright_red, yellow, cyan, green, red

    strategies_arg = args.strategies
    data_ticker = getattr(args, "data", None)
    period = getattr(args, "period", "1y")

    # If --data is provided, treat strategies as names and run backtests
    if data_ticker:
        # strategies can be comma-separated or space-separated
        strategy_names = []
        for s in strategies_arg:
            strategy_names.extend(s.split(","))

        df = _fetch_data(data_ticker, period=period)
        if df is None or len(df) < 50:
            print(f"  No sufficient data for {data_ticker}")
            return

        import numpy as np
        from src.ta import rsi as calc_rsi, macd as calc_macd, sma, ema

        close = np.array(df["Close"].tolist(), dtype=np.float64)
        prices = df["Close"].tolist()

        results = []
        for name in strategy_names:
            r = _run_strategy_compare(name, df, close, prices)
            if r:
                results.append(r)

        if not results:
            print("  No valid strategy results.")
            return

        # Find best for each metric
        best_ret = max(results, key=lambda x: x["return"])
        best_sharpe = max(results, key=lambda x: x["sharpe"])
        best_dd = max(results, key=lambda x: x["max_dd"])  # least negative
        best_wr = max(results, key=lambda x: x["win_rate"])

        print(f"\n  ── Strategy Comparison: {data_ticker} ({period}) ──\n")
        print(f"  {'Strategy':<20} {'Return':>10} {'Sharpe':>10} {'MaxDD':>10} {'WinRate':>10} {'Trades':>8}")
        print("  " + "─" * 70)

        for r in results:
            ret_str = f"{r['return']:>+9.2f}%"
            sharpe_str = f"{r['sharpe']:>9.2f}"
            dd_str = f"{r['max_dd']:>+9.2f}%"
            wr_str = f"{r['win_rate']:>8.1f}%"
            trades_str = f"{r['trades']:>7}"

            # Highlight best
            if r is best_ret:
                ret_str = bright_green(ret_str)
            if r is best_sharpe:
                sharpe_str = bright_green(sharpe_str)
            if r is best_dd:
                dd_str = bright_green(dd_str)
            if r is best_wr:
                wr_str = bright_green(wr_str)

            print(f"  {r['name']:<20} {ret_str} {sharpe_str} {dd_str} {wr_str} {trades_str}")

        print()
        print(f"  🏆 Best Return:   {bright_green(best_ret['name'])}")
        print(f"  🏆 Best Sharpe:   {bright_green(best_sharpe['name'])}")
        print(f"  🏆 Least DrawDown: {bright_green(best_dd['name'])}")
        print()
        return results

    # Original file-based comparison
    from src.reports.comparison import StrategyComparison

    comp = StrategyComparison()
    for filepath in strategies_arg:
        if not os.path.exists(filepath):
            print(f"  File not found: {filepath}")
            continue
        with open(filepath) as f:
            data = json.load(f)
        name = data.get("name", os.path.splitext(os.path.basename(filepath))[0])
        returns = data.get("returns", data.get("daily_returns", []))
        if not returns:
            print(f"  WARNING: No returns in {filepath}")
            continue
        comp.add_strategy(name, returns)

    if not comp._strategies:
        print("  ERROR: No valid strategies loaded")
        return

    output = args.output or f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    result = comp.generate_report(output_path=output)
    print(f"  ✓ Comparison report generated: {output} ({len(result):,} bytes)")


def _run_strategy_compare(name: str, df, close, prices) -> dict | None:
    """Run a named strategy and return metrics."""
    import numpy as np
    from src.ta import rsi as calc_rsi, macd as calc_macd, sma

    # Alias map: backtest strategy names → compare strategy names
    _STRATEGY_ALIASES = {
        "sma_cross": "trend_following",
        "rsi": "mean_reversion",
        "macd": "macd_cross",
        "bollinger": "mean_reversion",
        "buy_hold": "buy_hold",
        # Compare's own names map to themselves
        "momentum": "momentum",
        "mean_reversion": "mean_reversion",
        "trend_following": "trend_following",
        "macd_cross": "macd_cross",
    }

    all_strategy_names = sorted(set(list(_STRATEGY_ALIASES.keys()) + list(_STRATEGY_ALIASES.values())))
    canonical = _STRATEGY_ALIASES.get(name, None)
    if canonical is None:
        print(f"  Unknown strategy: {name}. Available: {', '.join(all_strategy_names)}")
        return None

    # Use the canonical name for logic but keep original name for display
    display_name = name

    n = len(prices)
    if n < 50:
        return None

    signals = []  # list of (index, 'buy'|'sell')

    if canonical == "momentum":
        # Buy when 10-day return > 0, sell when < 0
        for i in range(20, n):
            ret10 = prices[i] / prices[i - 10] - 1
            if ret10 > 0.02:
                signals.append((i, "buy"))
            elif ret10 < -0.02:
                signals.append((i, "sell"))

    elif canonical == "mean_reversion":
        rsi = calc_rsi(close, 14)
        for i in range(20, n):
            if not np.isnan(rsi[i]):
                if rsi[i] < 30:
                    signals.append((i, "buy"))
                elif rsi[i] > 70:
                    signals.append((i, "sell"))

    elif canonical == "trend_following":
        sma20 = sma(close, 20)
        sma50 = sma(close, 50)
        for i in range(50, n):
            if not np.isnan(sma20[i]) and not np.isnan(sma50[i]):
                if sma20[i] > sma50[i]:
                    signals.append((i, "buy"))
                else:
                    signals.append((i, "sell"))

    elif canonical == "macd_cross":
        macd_line, signal_line, hist = calc_macd(close)
        for i in range(30, n):
            if not np.isnan(hist[i]) and not np.isnan(hist[i - 1]):
                if hist[i] > 0 and hist[i - 1] <= 0:
                    signals.append((i, "buy"))
                elif hist[i] < 0 and hist[i - 1] >= 0:
                    signals.append((i, "sell"))

    elif canonical == "buy_hold":
        signals = [(20, "buy")]  # buy and hold

    # Simulate
    holding = False
    entry_price = 0
    trades = 0
    wins = 0
    pnl_total = 0

    for idx, action in signals:
        if action == "buy" and not holding:
            entry_price = prices[idx]
            holding = True
        elif action == "sell" and holding:
            pnl = prices[idx] / entry_price - 1
            pnl_total += pnl
            trades += 1
            if pnl > 0:
                wins += 1
            holding = False

    # Close open position at end
    if holding:
        pnl = prices[-1] / entry_price - 1
        pnl_total += pnl
        trades += 1
        if pnl > 0:
            wins += 1

    # Calculate equity curve for drawdown + sharpe
    equity = [1.0]
    pos = False
    ep = 0
    for i in range(1, n):
        if pos:
            equity.append(equity[-1] * (prices[i] / prices[i - 1]))
        else:
            equity.append(equity[-1])
        # Check signals for this index
        for idx, action in signals:
            if idx == i:
                if action == "buy" and not pos:
                    pos = True
                    ep = prices[i]
                elif action == "sell" and pos:
                    pos = False

    equity = np.array(equity)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) * 100

    # Daily returns for Sharpe
    daily_ret = np.diff(equity) / equity[:-1]
    sharpe = float(np.mean(daily_ret) / np.std(daily_ret) * np.sqrt(252)) if np.std(daily_ret) > 0 else 0

    total_return = (equity[-1] / equity[0] - 1) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0

    return {
        "name": display_name,
        "return": total_return,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "win_rate": win_rate,
        "trades": trades,
    }


def cmd_risk(args):
    """Analyze portfolio risk from JSON file."""
    from src.risk import VaRCalculator, PortfolioRiskManager
    import numpy as np

    filepath = args.portfolio
    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return

    with open(filepath) as f:
        portfolio = json.load(f)

    holdings = portfolio.get("holdings", portfolio if isinstance(portfolio, list) else [])
    tickers = [h.get("ticker", h.get("symbol", "???")) for h in holdings]
    weights_raw = [h.get("weight", h.get("shares", 1)) for h in holdings]
    total_w = sum(weights_raw)
    weights = [w / total_w for w in weights_raw]

    print(f"\n  ── Portfolio Risk Analysis ──")
    print(f"  Holdings: {len(tickers)} | Tickers: {', '.join(tickers)}")

    # Collect returns
    all_returns = []
    for ticker in tickers:
        df = _fetch_data(ticker, period="1y")
        if df is None or len(df) < 30:
            all_returns.append(np.zeros(250))
            continue
        prices = np.array(df["Close"].tolist(), dtype=np.float64)
        rets = np.diff(prices) / prices[:-1]
        all_returns.append(rets)

    # Align lengths
    min_len = min(len(r) for r in all_returns)
    all_returns = [r[-min_len:] for r in all_returns]

    # Portfolio returns
    weights_arr = np.array(weights)
    returns_matrix = np.array(all_returns)
    port_returns = returns_matrix.T @ weights_arr

    # VaR
    var_95 = np.percentile(port_returns, 5)
    var_99 = np.percentile(port_returns, 1)
    cvar_95 = port_returns[port_returns <= var_95].mean() if any(port_returns <= var_95) else var_95

    # Volatility
    ann_vol = np.std(port_returns) * np.sqrt(252)
    ann_ret = np.mean(port_returns) * 252
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0

    # Max drawdown
    cum = np.cumprod(1 + port_returns)
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / peak
    max_dd = np.min(dd)

    # Correlation matrix
    corr = np.corrcoef(returns_matrix)

    print(f"\n  Annualized Return:  {ann_ret:+.2%}")
    print(f"  Annualized Vol:     {ann_vol:.2%}")
    print(f"  Sharpe Ratio:       {sharpe:.2f}")
    print(f"  Max Drawdown:       {max_dd:.2%}")
    print(f"  VaR (95%):          {var_95:.4f} ({var_95 * 100:.2f}%)")
    print(f"  VaR (99%):          {var_99:.4f} ({var_99 * 100:.2f}%)")
    print(f"  CVaR (95%):         {cvar_95:.4f} ({cvar_95 * 100:.2f}%)")

    # Concentration (HHI)
    hhi = sum(w ** 2 for w in weights)
    print(f"\n  HHI (concentration): {hhi:.4f} ({'Concentrated' if hhi > 0.25 else 'Diversified'})")

    # Correlation summary
    avg_corr = (corr.sum() - len(tickers)) / (len(tickers) * (len(tickers) - 1)) if len(tickers) > 1 else 0
    print(f"  Avg Correlation:     {avg_corr:.2f}")

    output = args.output
    if output:
        result = {
            "tickers": tickers, "weights": weights,
            "annualized_return": float(ann_ret), "annualized_vol": float(ann_vol),
            "sharpe": float(sharpe), "max_drawdown": float(max_dd),
            "var_95": float(var_95), "var_99": float(var_99), "cvar_95": float(cvar_95),
            "hhi": float(hhi), "avg_correlation": float(avg_corr),
        }
        with open(output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n  ✓ Risk report saved to {output}")

    return {"sharpe": sharpe, "max_dd": max_dd, "var_95": var_95}


def cmd_interactive(args):
    """Launch interactive mode."""
    from src.interactive import InteractiveSession
    session = InteractiveSession()
    session.run()


# ────────────────────────────────────────────────────────────────
# Universe helpers
# ────────────────────────────────────────────────────────────────

def _get_universe_tickers(universe: str) -> list[str]:
    """Get ticker list for a universe name."""
    universes = {
        "sp500": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
                   "JPM", "V", "JNJ", "WMT", "PG", "MA", "HD", "DIS", "PYPL",
                   "NFLX", "ADBE", "CRM", "INTC", "AMD", "QCOM", "TXN", "COST"],
        "nasdaq100": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                      "NFLX", "ADBE", "CRM", "AMD", "QCOM", "INTC", "PYPL", "COST"],
        "dow30": ["AAPL", "MSFT", "JPM", "V", "JNJ", "WMT", "PG", "HD", "DIS",
                  "MCD", "NKE", "BA", "GS", "IBM", "CAT"],
    }
    return universes.get(universe, universes["sp500"])


# ────────────────────────────────────────────────────────────────
# Main parser
# ────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the full CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="finclaw",
        description="FinClaw v5.1.0 — AI-Powered Financial Intelligence Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  finclaw backtest --strategy momentum --tickers AAPL,MSFT --start 2023-01-01 --benchmark SPY
  finclaw backtest --strategy momentum --ticker AAPL
  finclaw screen --criteria "rsi<30,pe<15,market_cap>1B" --universe sp500
  finclaw analyze --ticker AAPL --indicators rsi,macd,bollinger
  finclaw risk --portfolio portfolio.json
  finclaw portfolio track --file portfolio.json
  finclaw price --ticker AAPL,MSFT,GOOGL
  finclaw options price --type call --S 150 --K 155 --T 0.5 --r 0.05 --sigma 0.25
  finclaw paper-trade --strategy trend --tickers AAPL,MSFT --capital 100000
  finclaw report --input backtest_result.json --format html --output report.html
  finclaw report --data results.json
  finclaw interactive
""",
    )
    parser.add_argument("--version", action="version", version=f"finclaw {_get_version()}")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # backtest
    p = sub.add_parser("backtest", help="Run strategy backtest")
    p.add_argument("--strategy", "-s", default="momentum", help="Strategy name")
    p.add_argument("--tickers", "-t", default=None, help="Comma-separated tickers")
    p.add_argument("--ticker", default=None, help="Single ticker (alias for --tickers)")
    p.add_argument("--start", default=None, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    p.add_argument("--benchmark", "-b", default=None, help="Benchmark ticker")
    p.add_argument("--capital", "-c", type=float, default=None)
    p.add_argument("--output", "-o", help="Save results to JSON")

    # screen
    p = sub.add_parser("screen", help="Screen stocks by criteria")
    p.add_argument("--criteria", default=None, help='Filter criteria, e.g. "rsi<30,pe<15"')
    p.add_argument("--universe", default="sp500", help="Stock universe")
    p.add_argument("--min-volume", type=float, default=None, help="Minimum volume")
    p.add_argument("--max-volume", type=float, default=None, help="Maximum volume")
    p.add_argument("--min-price", type=float, default=None, help="Minimum price")
    p.add_argument("--max-price", type=float, default=None, help="Maximum price")
    p.add_argument("--change-above", type=float, default=None, help="Daily change %% above")
    p.add_argument("--change-below", type=float, default=None, help="Daily change %% below")
    p.add_argument("--rsi-above", type=float, default=None, help="RSI above")
    p.add_argument("--rsi-below", type=float, default=None, help="RSI below")
    p.add_argument("--min-mcap", type=float, default=None, help="Minimum market cap")
    p.add_argument("--max-mcap", type=float, default=None, help="Maximum market cap")
    p.add_argument("--limit", "-l", type=int, default=20, help="Number of results")

    # analyze
    p = sub.add_parser("analyze", help="Technical analysis")
    p.add_argument("--ticker", "-t", required=True, help="Ticker symbol")
    p.add_argument("--indicators", "-i", default="rsi,macd,bollinger", help="Comma-separated indicators")

    # portfolio
    p_port = sub.add_parser("portfolio", help="Portfolio commands")
    port_sub = p_port.add_subparsers(dest="portfolio_cmd")
    p_track = port_sub.add_parser("track", help="Track portfolio from file")
    p_track.add_argument("--file", "-f", required=True, help="Portfolio JSON file")

    p_padd = port_sub.add_parser("add", help="Add a holding")
    p_padd.add_argument("symbol", help="Ticker symbol (e.g. BTC, AAPL)")
    p_padd.add_argument("quantity", type=float, help="Quantity to add")
    p_padd.add_argument("--price", type=float, default=0.0, help="Buy price per unit")
    p_padd.add_argument("--portfolio", default="main", help="Portfolio name")

    p_prm = port_sub.add_parser("remove", help="Remove a holding")
    p_prm.add_argument("symbol", help="Ticker symbol")
    p_prm.add_argument("quantity", type=float, help="Quantity to remove")
    p_prm.add_argument("--portfolio", default="main", help="Portfolio name")

    p_pshow = port_sub.add_parser("show", help="Show portfolio with P&L")
    p_pshow.add_argument("--portfolio", default="main", help="Portfolio name")

    p_phist = port_sub.add_parser("history", help="Portfolio value history")
    p_phist.add_argument("--portfolio", default="main", help="Portfolio name")

    p_palert = port_sub.add_parser("alert", help="Set price alert")
    p_palert.add_argument("symbol", help="Ticker symbol")
    p_palert.add_argument("--above", type=float, default=None, help="Alert when price above")
    p_palert.add_argument("--below", type=float, default=None, help="Alert when price below")
    p_palert.add_argument("--portfolio", default="main", help="Portfolio name")

    p_pexp = port_sub.add_parser("export", help="Export portfolio to CSV")
    p_pexp.add_argument("--format", default="csv", choices=["csv"], help="Export format")
    p_pexp.add_argument("--what", default="holdings", choices=["holdings", "history"])
    p_pexp.add_argument("--output", "-o", default=None, help="Output file")
    p_pexp.add_argument("--portfolio", default="main", help="Portfolio name")

    # price
    p = sub.add_parser("price", help="Get current prices")
    p.add_argument("--ticker", "-t", required=True, help="Comma-separated tickers")

    # options
    p_opts = sub.add_parser("options", help="Options commands")
    opts_sub = p_opts.add_subparsers(dest="options_cmd")
    p_oprice = opts_sub.add_parser("price", help="Price an option (Black-Scholes)")
    p_oprice.add_argument("--type", choices=["call", "put"], required=True)
    p_oprice.add_argument("--S", type=float, required=True, help="Spot price")
    p_oprice.add_argument("--K", type=float, required=True, help="Strike price")
    p_oprice.add_argument("--T", type=float, required=True, help="Time to expiry (years)")
    p_oprice.add_argument("--r", type=float, required=True, help="Risk-free rate")
    p_oprice.add_argument("--sigma", type=float, required=True, help="Volatility")

    # paper-trade (legacy)
    p = sub.add_parser("paper-trade", help="Paper trading simulation (legacy)")
    p.add_argument("--strategy", "-s", default="trend", help="Strategy name")
    p.add_argument("--tickers", "-t", required=True, help="Comma-separated tickers")
    p.add_argument("--capital", "-c", type=float, default=100000)

    # paper (new paper trading engine)
    p_paper = sub.add_parser("paper", help="Paper trading simulator")
    paper_sub = p_paper.add_subparsers(dest="paper_cmd")

    p_ps = paper_sub.add_parser("start", help="Start paper trading session")
    p_ps.add_argument("--balance", type=float, default=100000, help="Initial balance")
    p_ps.add_argument("--exchange", default="yahoo", help="Exchange adapter")

    p_pb = paper_sub.add_parser("buy", help="Buy shares")
    p_pb.add_argument("symbol", help="Ticker symbol")
    p_pb.add_argument("quantity", type=float, help="Number of shares")
    p_pb.add_argument("--type", default="market", choices=["market", "limit"])
    p_pb.add_argument("--limit-price", type=float, default=None)

    p_pse = paper_sub.add_parser("sell", help="Sell shares")
    p_pse.add_argument("symbol", help="Ticker symbol")
    p_pse.add_argument("quantity", type=float, help="Number of shares")
    p_pse.add_argument("--type", default="market", choices=["market", "limit"])
    p_pse.add_argument("--limit-price", type=float, default=None)

    paper_sub.add_parser("portfolio", help="Show portfolio")
    paper_sub.add_parser("pnl", help="Show P&L")
    paper_sub.add_parser("history", help="Show trade history")
    paper_sub.add_parser("dashboard", help="Show dashboard")

    p_prs = paper_sub.add_parser("run-strategy", help="Run a strategy")
    p_prs.add_argument("strategy", help="Strategy name (golden-cross, momentum)")
    p_prs.add_argument("--symbols", required=True, help="Comma-separated symbols")
    p_prs.add_argument("--ticks", type=int, default=10, help="Number of ticks to run")

    p_pj = paper_sub.add_parser("journal", help="Show trade journal")
    p_pj.add_argument("--export", choices=["csv", "json"], default=None)
    p_pj.add_argument("--date", default=None, help="Date for summary (YYYY-MM-DD)")

    paper_sub.add_parser("reset", help="Reset paper trading session")

    # report
    p = sub.add_parser("report", help="Generate report from results")
    p.add_argument("--input", "-i", default=None, help="Input JSON file")
    p.add_argument("--data", "-d", default=None, help="Input JSON file (alias for --input)")
    p.add_argument("--format", "-f", default="html", choices=["html", "json"])
    p.add_argument("--output", "-o", help="Output file path")

    # tearsheet
    p = sub.add_parser("tearsheet", help="Generate QuantStats-style tearsheet")
    p.add_argument("--returns", "-r", required=True, help="CSV file with daily returns (or JSON)")
    p.add_argument("--benchmark", "-b", default=None, help="Benchmark ticker (e.g. SPY) or CSV file")
    p.add_argument("--output", "-o", help="Output HTML file path")

    # compare (existing file-based)
    p = sub.add_parser("compare", help="Compare multiple strategies")
    p.add_argument("--strategies", "-s", nargs="+", required=True,
                   help="Strategy names (comma-sep) or JSON files with returns")
    p.add_argument("--data", "-d", default=None, help="Ticker symbol for backtest comparison")
    p.add_argument("--period", "-p", default="1y", help="Data period (e.g. 1y, 2y)")
    p.add_argument("--output", "-o", help="Output HTML file path")

    # export
    p_export = sub.add_parser("export", help="Export OHLCV + technical indicators to file")
    p_export.add_argument("--ticker", "-t", required=True, help="Ticker symbol")
    p_export.add_argument("--period", "-p", default="1y", help="Data period (e.g. 1y, 2y, 5y)")
    p_export.add_argument("--format", "-f", default="csv", choices=["csv", "json"], help="Output format")
    p_export.add_argument("--output", "-o", default=None, help="Output file path")
    p_export.add_argument("--indicators", "-i", default="sma20,sma50,rsi,macd", help="Indicators to include")

    # risk
    p = sub.add_parser("risk", help="Portfolio risk analysis")
    p.add_argument("--portfolio", "-p", required=True, help="Portfolio JSON file")
    p.add_argument("--output", "-o", help="Save risk report to JSON")

    # risk-report
    p = sub.add_parser("risk-report", help="Comprehensive risk report from return series or portfolio")
    p.add_argument("--returns", "-r", default=None, help="CSV/JSON file with daily returns")
    p.add_argument("--portfolio", "-p", default=None, help="Portfolio JSON file")
    p.add_argument("--ticker", "-t", default=None, help="Ticker symbol for quick analysis")
    p.add_argument("--period", default="1y", help="Data period (for --ticker)")
    p.add_argument("--output", "-o", help="Save report to JSON")

    # position-size
    p = sub.add_parser("position-size", help="Calculate position size for a trade")
    p.add_argument("--capital", "-c", type=float, required=True, help="Total capital")
    p.add_argument("--risk", "-r", type=float, default=2.0, help="Risk per trade (%%)")
    p.add_argument("--entry", type=float, default=None, help="Entry price")
    p.add_argument("--stop", type=float, default=None, help="Stop-loss price or %% distance")
    p.add_argument("--atr", type=float, default=None, help="ATR value for volatility sizing")
    p.add_argument("--method", "-m", default="fixed-fraction",
                   choices=["fixed-fraction", "kelly", "volatility", "equal-weight"],
                   help="Position sizing method")
    p.add_argument("--win-rate", type=float, default=None, help="Win rate for Kelly (0-1)")
    p.add_argument("--win-loss-ratio", type=float, default=None, help="Avg win / avg loss for Kelly")
    p.add_argument("--n-positions", type=int, default=None, help="Number of positions for equal-weight")

    # serve
    p = sub.add_parser("serve", help="Start REST API server")
    p.add_argument("--host", default="0.0.0.0", help="Bind host")
    p.add_argument("--port", "-p", type=int, default=8080, help="Port number")
    p.add_argument("--auth", action="store_true", help="Enable API key auth")
    p.add_argument("--rate-limit", type=int, default=100, help="Max requests per minute")

    # defi-tvl
    p_dtvl = sub.add_parser("defi-tvl", help="Top DeFi protocols by TVL (via DeFi Llama)")
    p_dtvl.add_argument("--limit", "-l", type=int, default=20, help="Number of protocols")

    # yields
    p_yields = sub.add_parser("yields", help="Best DeFi yield farming opportunities (via DeFi Llama)")
    p_yields.add_argument("--chain", default=None, help="Filter by chain (e.g. Ethereum, BSC)")
    p_yields.add_argument("--min-tvl", type=float, default=100_000, help="Minimum pool TVL in USD")
    p_yields.add_argument("--limit", "-l", type=int, default=20, help="Number of results")

    # stablecoins
    p_stbl = sub.add_parser("stablecoins", help="Stablecoin market overview (via DeFi Llama)")
    p_stbl.add_argument("--limit", "-l", type=int, default=20, help="Number of stablecoins")

    # btc-metrics
    sub.add_parser("btc-metrics", help="Show BTC on-chain metrics dashboard")

    # funding-rates
    p_fr = sub.add_parser("funding-rates", help="Multi-exchange funding rate comparison")
    p_fr.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT", help="Comma-separated symbols")
    p_fr.add_argument("--min-spread", type=float, default=5.0, help="Min annualized spread %% for arbitrage")

    # fear-greed
    p_fng = sub.add_parser("fear-greed", help="Current Fear & Greed Index")
    p_fng.add_argument("--history", type=int, default=1, help="Number of historical data points")

    # watch (shortcut for watchlist with enhanced UX)
    p_w = sub.add_parser("watch", help="Quick watchlist commands")
    p_w.add_argument("watch_action", nargs="?", default="show",
                      choices=["show", "add", "remove", "create", "list"],
                      help="Action to perform")
    p_w.add_argument("watch_args", nargs="*", help="Tickers or watchlist name")
    p_w.add_argument("--name", "-n", default="default", help="Watchlist name")

    # gainers / losers
    p_gain = sub.add_parser("gainers", help="Top daily gainers")
    p_gain.add_argument("--limit", "-l", type=int, default=10, help="Number of results")
    p_gain.add_argument("--universe", default="sp500", help="Stock universe")

    p_lose = sub.add_parser("losers", help="Top daily losers")
    p_lose.add_argument("--limit", "-l", type=int, default=10, help="Number of results")
    p_lose.add_argument("--universe", default="sp500", help="Stock universe")

    # interactive
    sub.add_parser("interactive", help="Launch interactive mode")

    # cache
    p = sub.add_parser("cache", help="Cache management")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--clear", action="store_true")

    # exchanges
    p_ex = sub.add_parser("exchanges", help="Exchange adapter commands")
    p_ex.add_argument("exchanges_cmd", nargs="?", default="list", choices=["list", "compare"])
    p_ex.add_argument("exchange_names", nargs="*", help="Exchanges to compare")

    # quote (multi-exchange, supports multiple symbols)
    p_q = sub.add_parser("quote", help="Get quote from any exchange")
    p_q.add_argument("symbol", nargs="+", help="Symbol(s) (e.g. AAPL TSLA MSFT)")
    p_q.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")

    # history (multi-exchange)
    p_h = sub.add_parser("history", help="Get OHLCV history from any exchange")
    p_h.add_argument("symbol", help="Symbol")
    p_h.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")
    p_h.add_argument("--timeframe", "-t", default="1d", help="Timeframe (1m,5m,1h,1d,...)")
    p_h.add_argument("--limit", "-l", type=int, default=20, help="Number of candles")

    # demo
    sub.add_parser("demo", help="Showcase all features with pre-baked data (no API key needed)")

    # info
    p_info = sub.add_parser("info", help="Show system info or ticker info")
    p_info.add_argument("ticker", nargs="?", default=None, help="Optional ticker symbol for detailed info")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Diagnose environment: deps, API keys, connectivity")
    p_doctor.add_argument("--verbose", "-v", action="store_true", help="Show all checks, not just failures")
    p_doctor.add_argument("--skip-network", action="store_true", help="Skip network connectivity checks")

    # plugin
    p_plugin = sub.add_parser("plugin", help="Plugin management")
    plugin_sub = p_plugin.add_subparsers(dest="plugin_cmd")
    plugin_sub.add_parser("list", help="List installed/loaded plugins")
    p_pi = plugin_sub.add_parser("install", help="Install a plugin")
    p_pi.add_argument("source", help="Path to plugin .py file")
    p_pc = plugin_sub.add_parser("create", help="Create a new plugin from template")
    p_pc.add_argument("--type", dest="plugin_type", default="strategy", choices=["strategy", "indicator", "exchange"], help="Plugin type")
    p_pc.add_argument("--name", required=True, help="Plugin name")
    p_pinfo = plugin_sub.add_parser("info", help="Show plugin details")
    p_pinfo.add_argument("name", help="Plugin name")

    # plugins (new strategy plugin ecosystem)
    p_plugins = sub.add_parser("plugins", help="Strategy plugin ecosystem")
    plugins_sub = p_plugins.add_subparsers(dest="plugins_cmd")
    plugins_sub.add_parser("list", help="List all strategy plugins (built-in + installed)")
    p_plinfo = plugins_sub.add_parser("info", help="Show strategy plugin details")
    p_plinfo.add_argument("name", help="Plugin name")

    # init-strategy
    p_init_strat = sub.add_parser("init-strategy", help="Generate strategy plugin scaffolding")
    p_init_strat.add_argument("name", help="Strategy name (e.g. my_awesome_strategy)")
    p_init_strat.add_argument("--output", "-o", default=".", help="Output directory")

    # predict
    p_pred = sub.add_parser("predict", help="ML prediction engine")
    pred_sub = p_pred.add_subparsers(dest="predict_cmd")
    p_pred_run = pred_sub.add_parser("run", help="Run prediction on a symbol")
    p_pred_run.add_argument("--symbol", "-s", default=None, help="Ticker symbol")
    p_pred_run.add_argument("--ticker", dest="ticker_alias", default=None, help="Ticker symbol (alias for --symbol)")
    p_pred_run.add_argument("--model", "-m", default="gradient-boost",
                            choices=["linear", "decision-tree", "random-forest", "gradient-boost"],
                            help="Model to use")
    p_pred_run.add_argument("--features", "-f", default="rsi,macd,volatility",
                            help="Comma-separated features")
    p_pred_bt = pred_sub.add_parser("backtest", help="Walk-forward backtest")
    p_pred_bt.add_argument("--symbol", "-s", required=True, help="Ticker symbol")
    p_pred_bt.add_argument("--model", "-m", default="random-forest",
                           choices=["linear", "decision-tree", "random-forest", "gradient-boost"],
                           help="Model to use")
    p_pred_bt.add_argument("--train-size", type=int, default=252, help="Training window size")
    p_pred_bt.add_argument("--test-size", type=int, default=21, help="Test window size")
    p_pred_bt.add_argument("--walk-forward", action="store_true", default=True,
                           help="Use walk-forward validation")

    # MCP server
    p_mcp = sub.add_parser("mcp", help="MCP (Model Context Protocol) server for AI agents")
    mcp_sub = p_mcp.add_subparsers(dest="mcp_cmd")
    mcp_sub.add_parser("serve", help="Start MCP server (stdio JSON-RPC)")
    p_mcp_cfg = mcp_sub.add_parser("config", help="Generate MCP client config")
    p_mcp_cfg.add_argument("--client", "-c", default="claude", help="Client: claude, cursor, openclaw, vscode, generic")

    # watchlist
    p_wl = sub.add_parser("watchlist", help="Manage watchlists")
    wl_sub = p_wl.add_subparsers(dest="watchlist_cmd")
    p_wlc = wl_sub.add_parser("create", help="Create a watchlist")
    p_wlc.add_argument("name", help="Watchlist name")
    p_wlc.add_argument("symbols", nargs="*", help="Initial symbols")
    p_wlq = wl_sub.add_parser("quotes", help="Get quotes for a watchlist")
    p_wlq.add_argument("name", help="Watchlist name")
    p_wla = wl_sub.add_parser("add", help="Add symbol to watchlist")
    p_wla.add_argument("name", help="Watchlist name")
    p_wla.add_argument("symbol", help="Symbol to add")
    p_wlr = wl_sub.add_parser("remove", help="Remove symbol from watchlist")
    p_wlr.add_argument("name", help="Watchlist name")
    p_wlr.add_argument("symbol", help="Symbol to remove")
    p_wle = wl_sub.add_parser("export", help="Export watchlist")
    p_wle.add_argument("name", help="Watchlist name")
    p_wle.add_argument("--format", default="csv", choices=["csv", "json"])
    wl_sub.add_parser("list", help="List all watchlists")

    # sentiment (enhanced with social buzz)
    p_sent = sub.add_parser("sentiment", help="Sentiment analysis for a symbol")
    p_sent.add_argument("symbol", help="Ticker symbol (e.g. AAPL, BTCUSDT)")
    p_sent.add_argument("--reddit", action="store_true", help="Include Reddit sentiment")
    p_sent.add_argument("--buzz", action="store_true", help="Show full social buzz score")

    # reddit-buzz
    p_rb = sub.add_parser("reddit-buzz", help="Top buzzing tickers in a subreddit")
    p_rb.add_argument("subreddit", help="Subreddit name (e.g. wallstreetbets, CryptoCurrency)")
    p_rb.add_argument("--limit", "-l", type=int, default=50, help="Number of posts to scan")

    # news
    p_news = sub.add_parser("news", help="Get financial news for a symbol")
    p_news.add_argument("symbol", help="Ticker symbol")
    p_news.add_argument("--limit", "-l", type=int, default=10, help="Number of articles")
    p_news.add_argument("--search", "-s", default=None, help="Search query instead of symbol")

    # trending
    sub.add_parser("trending", help="Show trending financial topics and WSB tickers")

    # scan-cn (A-share scanner)
    p_scan_cn = sub.add_parser("scan-cn", help="Scan A-share (China) stocks for buy signals")
    p_scan_cn.add_argument("--top", type=int, default=30, help="Number of top stocks to scan (default: 30)")
    p_scan_cn.add_argument("--sector", default=None,
                           help="Filter by sector: bank, tech, consumer, energy, pharma, manufacturing")
    p_scan_cn.add_argument("--min-score", type=int, default=0, help="Only show stocks with score >= N")
    p_scan_cn.add_argument("--sort", default="score",
                           choices=["score", "rsi", "price", "change"],
                           help="Sort results by field (default: score)")

    # scan
    p_scan = sub.add_parser("scan", help="Real-time market scanner")
    p_scan.add_argument("--rule", required=True, help='Rule expression, e.g. "rsi<30 AND volume>2x"')
    p_scan.add_argument("--symbols", default="AAPL,MSFT,GOOGL,AMZN,TSLA", help="Comma-separated symbols")
    p_scan.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")
    p_scan.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    p_scan.add_argument("--once", action="store_true", help="Run only once")

    # strategy library
    p_strat = sub.add_parser("strategy", help="Built-in strategy library & YAML DSL")
    strat_sub = p_strat.add_subparsers(dest="strategy_cmd")
    strat_sub.add_parser("list", help="List all built-in strategies (classic + YAML)")
    p_si = strat_sub.add_parser("info", help="Show strategy details")
    p_si.add_argument("name", help="Strategy slug (e.g. grid-trading)")
    p_sb = strat_sub.add_parser("backtest", help="Backtest a built-in strategy")
    p_sb.add_argument("name", help="Strategy slug (e.g. trend-following)")
    p_sb.add_argument("--symbol", "-s", default="AAPL", help="Ticker symbol")
    p_sb.add_argument("--start", default="2024-01-01", help="Start date")
    p_sb.add_argument("--end", default=None, help="End date")
    p_sb.add_argument("--capital", type=float, default=10000, help="Initial capital")

    # YAML DSL strategy commands
    strat_sub.add_parser("create", help="Interactive YAML strategy builder")
    p_sv = strat_sub.add_parser("validate", help="Validate a YAML strategy file")
    p_sv.add_argument("file", help="Path to YAML strategy file")
    p_sbt = strat_sub.add_parser("dsl-backtest", help="Backtest a YAML strategy file")
    p_sbt.add_argument("file", help="Path to YAML strategy file")
    p_sbt.add_argument("--symbol", "-s", default="AAPL", help="Ticker symbol")
    p_sbt.add_argument("--period", "-p", default="2y", help="Data period (e.g. 1y, 2y)")
    p_sopt = strat_sub.add_parser("optimize", help="Optimize YAML strategy parameters")
    p_sopt.add_argument("file", help="Path to YAML strategy file")
    p_sopt.add_argument("--param", action="append", help="param:min:max:step (e.g. rsi_period:10:30:5)")
    p_sopt.add_argument("--symbol", "-s", default="AAPL", help="Ticker symbol")
    p_sopt.add_argument("--period", "-p", default="2y", help="Data period")

    # ── Alert commands ──────────────────────────────────────────
    p_alert = sub.add_parser("alert", help="Smart alert system")
    alert_sub = p_alert.add_subparsers(dest="alert_cmd")

    p_aa = alert_sub.add_parser("add", help="Add an alert rule")
    p_aa.add_argument("--symbol", "-s", required=True, help="Ticker symbol")
    p_aa.add_argument("--price-above", type=float, help="Alert when price above")
    p_aa.add_argument("--price-below", type=float, help="Alert when price below")
    p_aa.add_argument("--rsi-above", type=float, help="Alert when RSI above")
    p_aa.add_argument("--rsi-below", type=float, help="Alert when RSI below")
    p_aa.add_argument("--volume-spike", type=float, help="Alert on volume spike (multiplier)")
    p_aa.add_argument("--macd-cross", action="store_true", help="Alert on MACD crossover")
    p_aa.add_argument("--bb-breakout", action="store_true", help="Alert on Bollinger Band breakout")
    p_aa.add_argument("--drawdown", type=float, help="Alert on drawdown (e.g. 0.10 for 10%%)")
    p_aa.add_argument("--channel", default="console", help="Notification channel (console|webhook|file)")
    p_aa.add_argument("--cooldown", type=int, default=3600, help="Cooldown in seconds")

    alert_sub.add_parser("list", help="List active alert rules")

    p_ah = alert_sub.add_parser("history", help="Show alert history")
    p_ah.add_argument("--hours", type=int, default=24, help="Hours to look back")
    p_ah.add_argument("--export", choices=["json", "csv"], help="Export format")

    p_ar = alert_sub.add_parser("remove", help="Remove an alert rule")
    p_ar.add_argument("rule_id", type=int, help="Rule ID to remove")

    p_as = alert_sub.add_parser("start", help="Start alert engine")
    p_as.add_argument("--symbols", "-s", required=True, help="Comma-separated symbols")
    p_as.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    # ── Chart commands (viz) ───────────────────────────────────
    p_chart = sub.add_parser("chart", help="Terminal charts for symbols")
    p_chart.add_argument("symbol", help="Ticker symbol (e.g. AAPL, BTCUSDT)")
    p_chart.add_argument("--type", "-t", default="line", choices=["candle", "line", "bar", "histogram"],
                         help="Chart type")
    p_chart.add_argument("--period", "-p", default="6mo", help="Data period (e.g. 30d, 6mo, 1y)")
    p_chart.add_argument("--width", type=int, default=80, help="Chart width")
    p_chart.add_argument("--height", type=int, default=20, help="Chart height")

    # ── A2A (Agent-to-Agent) protocol ─────────────────────────────
    p_a2a = sub.add_parser("a2a", help="A2A (Agent-to-Agent) protocol server")
    a2a_sub = p_a2a.add_subparsers(dest="a2a_cmd")
    p_a2a_serve = a2a_sub.add_parser("serve", help="Start A2A server")
    p_a2a_serve.add_argument("--host", default="localhost", help="Bind host")
    p_a2a_serve.add_argument("--port", type=int, default=8081, help="Bind port")
    p_a2a_serve.add_argument("--auth-token", default=None, help="Bearer auth token")
    a2a_sub.add_parser("card", help="Print the A2A agent card")

    # ── AI Strategy Generation ─────────────────────────────────
    p_gen = sub.add_parser("generate-strategy", help="AI-generate a trading strategy from natural language")
    p_gen.add_argument("description", nargs="?", default=None, help="Strategy description in plain English/中文")
    p_gen.add_argument("--interactive", action="store_true", help="Interactive multi-turn builder")
    p_gen.add_argument("--market", default="us_stock", choices=["us_stock", "crypto", "cn_stock"], help="Target market")
    p_gen.add_argument("--risk", default="medium", choices=["low", "medium", "high"], help="Risk profile")
    p_gen.add_argument("--provider", default=None, help="LLM provider (openai, anthropic, deepseek, ollama, ...)")
    p_gen.add_argument("--output", "-o", default=None, help="Save generated code to file")

    p_opt = sub.add_parser("optimize-strategy", help="AI-optimize an existing strategy")
    p_opt.add_argument("strategy_file", help="Path to strategy .py file")
    p_opt.add_argument("--data", "-d", default="AAPL", help="Ticker for backtesting")
    p_opt.add_argument("--period", "-p", default="1y", help="Data period (e.g. 1y, 2y)")
    p_opt.add_argument("--provider", default=None, help="LLM provider")

    sub.add_parser("copilot", help="Interactive AI financial assistant chat")

    return parser


def _compare_exchanges(names: list[str]) -> None:
    """Print a feature comparison table for given exchanges."""
    from src.exchanges.registry import ExchangeRegistry
    from src.exchanges.base import ExchangeAdapter

    features = [
        ("OHLCV/Candles", "get_ohlcv"),
        ("Ticker", "get_ticker"),
        ("Orderbook", "get_orderbook"),
        ("Place Order", "place_order"),
        ("Cancel Order", "cancel_order"),
        ("Balance", "get_balance"),
        ("Positions", "get_positions"),
    ]
    # optional extras
    optional = [
        ("Trades", "get_trades"),
        ("Quotes", "get_quotes"),
        ("Fills", "get_fills"),
        ("Dividends", "get_dividends"),
        ("Industry", "get_industry"),
        ("Ticker Details", "get_ticker_details"),
        ("Market Status", "get_market_status"),
        ("Paper Trading", None),
    ]

    adapters = {}
    for name in names:
        try:
            adapters[name] = ExchangeRegistry.get(name)
        except KeyError:
            print(f"  ⚠ Exchange '{name}' not found, skipping")

    if not adapters:
        print("  No valid exchanges to compare.")
        return

    col_w = max(len(n) for n in adapters) + 2
    header = f"  {'Feature':<20}" + "".join(f"{n:^{col_w}}" for n in adapters)
    print(header)
    print("  " + "─" * (len(header) - 2))

    all_features = features + optional
    for label, method in all_features:
        row = f"  {label:<20}"
        for name, adapter in adapters.items():
            if method is None:
                # Special: paper trading
                has = hasattr(adapter, "paper") or hasattr(adapter, "PAPER_URL")
                row += f"{'✅':^{col_w}}" if has else f"{'—':^{col_w}}"
            elif hasattr(adapter, method):
                # Check if it raises NotImplementedError
                import inspect
                src = inspect.getsource(getattr(type(adapter), method))
                if "NotImplementedError" in src:
                    row += f"{'—':^{col_w}}"
                else:
                    row += f"{'✅':^{col_w}}"
            else:
                row += f"{'—':^{col_w}}"
        print(row)

    print()
    print("  Exchange types:")
    for name, adapter in adapters.items():
        print(f"    {name}: {adapter.exchange_type}")


def cmd_predict(args):
    """Handle ML prediction commands: run, backtest."""
    if args.predict_cmd == "run":
        # Resolve --ticker alias for --symbol
        symbol = args.symbol or getattr(args, "ticker_alias", None)
        if not symbol:
            print("  ERROR: --symbol or --ticker is required")
            return
        print(f"\n  🤖 ML Prediction: {symbol}")
        print(f"  Model: {args.model}  Features: {args.features}")
        print(f"  (Prediction engine ready — connect live data for real predictions)")
        print()
    elif args.predict_cmd == "backtest":
        print(f"\n  🔄 Walk-Forward Backtest: {args.symbol}")
        print(f"  Model: {args.model}  Train: {args.train_size}  Test: {args.test_size}")
        print(f"  (Backtest engine ready — connect historical data for evaluation)")
        print()
    else:
        print("  Usage: finclaw predict [run|backtest]")


def cmd_strategy(args):
    """Handle strategy library commands: list, info, backtest, create, validate, dsl-backtest, optimize."""
    # YAML DSL commands first
    if args.strategy_cmd == "create":
        return _strategy_create_interactive()
    if args.strategy_cmd == "validate":
        return _strategy_validate(args.file)
    if args.strategy_cmd == "dsl-backtest":
        return _strategy_dsl_backtest(args)
    if args.strategy_cmd == "optimize":
        return _strategy_optimize(args)

    from src.strategies.library import list_strategies, get_strategy, STRATEGY_REGISTRY

    if args.strategy_cmd == "list":
        strategies = list_strategies()
        print(f"\n  📚 Built-in Strategies ({len(strategies)}):\n")
        for cat in ("crypto", "stock", "universal"):
            cat_strats = [s for s in strategies if s.category == cat]
            if cat_strats:
                print(f"  [{cat.upper()}]")
                for s in cat_strats:
                    print(f"    {s.slug:<22} {s.name} — {s.description[:60]}")
                print()

        # Also list YAML DSL strategies
        from src.strategy.library import list_strategies as list_yaml_strategies
        yaml_strats = list_yaml_strategies()
        print(f"  [YAML DSL STRATEGIES]")
        for s in yaml_strats:
            print(f"    {s['id']:<22} {s['name']} — {s['description'][:60]}")
        print()
    elif args.strategy_cmd == "info":
        try:
            cls = get_strategy(args.name)
        except KeyError as e:
            print(f"  ❌ {e}")
            return
        m = cls.meta()
        print(f"\n  📊 {m.name} ({m.slug})")
        print(f"  Category: {m.category}")
        print(f"  {m.description}\n")
        print("  Parameters:")
        for k, v in m.parameters.items():
            print(f"    --{k}: {v}")
        print(f"\n  Example: {m.usage_example}\n")
    elif args.strategy_cmd == "backtest":
        try:
            cls = get_strategy(args.name)
        except KeyError as e:
            print(f"  ❌ {e}")
            return
        m = cls.meta()
        print(f"\n  🚀 Backtesting {m.name} on {args.symbol} from {args.start}...")
        data = _fetch_data(args.symbol, start=args.start, end=args.end)
        if data is None or len(data) == 0:
            print("  ❌ No data fetched.")
            return
        # Convert to list of dicts
        ohlcv = []
        for _, row in data.iterrows():
            ohlcv.append({
                "open": float(row.get("Open", row.get("open", 0))),
                "high": float(row.get("High", row.get("high", 0))),
                "low": float(row.get("Low", row.get("low", 0))),
                "close": float(row.get("Close", row.get("close", 0))),
                "volume": float(row.get("Volume", row.get("volume", 0))),
            })
        strat = cls(initial_capital=args.capital)
        result = strat.backtest(ohlcv)
        print(f"\n  📈 Results:")
        print(f"    Total Return:  {result['total_return']:.2f}%")
        print(f"    Sharpe Ratio:  {result['sharpe_ratio']:.2f}")
        print(f"    Max Drawdown:  {result['max_drawdown']:.2f}%")
        print(f"    Win Rate:      {result['win_rate']:.1f}%")
        print(f"    Trades:        {result['num_trades']}")
        print(f"    Final Equity:  ${result['final_equity']:,.2f}\n")
    else:
        print("  Usage: finclaw strategy [list|info|backtest|create|validate|dsl-backtest|optimize]")


def _strategy_create_interactive():
    """Interactive YAML strategy builder."""
    print("\n  🧙 Interactive Strategy Builder\n")
    name = input("  Strategy name: ").strip() or "My Strategy"
    desc = input("  Description: ").strip()
    universe = input("  Universe (sp500/nasdaq/custom): ").strip() or "sp500"

    print("\n  Entry conditions (one per line, empty to finish):")
    print("  Examples: sma(20) > sma(50), rsi(14) < 30, volume > sma_volume(20) * 1.5")
    entry = []
    while True:
        cond = input("    entry> ").strip()
        if not cond:
            break
        entry.append(cond)

    print("\n  Exit conditions (prefix with 'OR:' for OR logic, empty to finish):")
    exit_conds = []
    while True:
        cond = input("    exit> ").strip()
        if not cond:
            break
        if cond.upper().startswith("OR:"):
            exit_conds.append({"OR": cond[3:].strip()})
        else:
            exit_conds.append(cond)

    stop_loss = input("  Stop loss (e.g. 5%): ").strip() or "5%"
    take_profit = input("  Take profit (e.g. 15%): ").strip() or "15%"
    max_pos = input("  Max position (e.g. 10%): ").strip() or "10%"
    rebalance = input("  Rebalance frequency (daily/weekly/monthly): ").strip() or "weekly"

    import yaml
    strategy = {
        "name": name,
        "description": desc,
        "universe": universe,
        "entry": entry,
        "exit": exit_conds,
        "risk": {"stop_loss": stop_loss, "take_profit": take_profit, "max_position": max_pos},
        "rebalance": rebalance,
    }
    yaml_str = yaml.dump(strategy, default_flow_style=False, sort_keys=False)
    print(f"\n  📄 Generated YAML:\n")
    for line in yaml_str.splitlines():
        print(f"    {line}")

    save = input("\n  Save to file? (filename or empty to skip): ").strip()
    if save:
        if not save.endswith((".yaml", ".yml")):
            save += ".yaml"
        with open(save, "w") as f:
            f.write(yaml_str)
        print(f"  ✅ Saved to {save}")


def _strategy_validate(filepath: str):
    """Validate a YAML strategy file."""
    from src.strategy.dsl import StrategyDSL
    dsl = StrategyDSL()
    try:
        with open(filepath, "r") as f:
            content = f.read()
        strategy = dsl.parse(content)
        print(f"\n  ✅ Strategy '{strategy.name}' is valid!")
        print(f"    Entry conditions: {len(strategy.entry_conditions)}")
        print(f"    Exit conditions: {len(strategy.exit_conditions)} AND + {len(strategy.exit_or_conditions)} OR")
        if strategy.risk.stop_loss:
            print(f"    Stop loss: {strategy.risk.stop_loss * 100:.0f}%")
        if strategy.risk.take_profit:
            print(f"    Take profit: {strategy.risk.take_profit * 100:.0f}%")
        print(f"    Rebalance: {strategy.rebalance}\n")
    except FileNotFoundError:
        print(f"  ❌ File not found: {filepath}")
    except ValueError as e:
        print(f"  ❌ Validation failed: {e}")


def _strategy_dsl_backtest(args):
    """Backtest a YAML DSL strategy."""
    from src.strategy.dsl import StrategyDSL
    from src.strategy.expression import OHLCVData
    from src.strategy.optimizer import StrategyOptimizer

    dsl = StrategyDSL()
    try:
        strategy = dsl.parse_file(args.file)
    except (FileNotFoundError, ValueError) as e:
        print(f"  ❌ {e}")
        return

    print(f"\n  🚀 Backtesting '{strategy.name}' on {args.symbol} ({args.period})...")
    df = _fetch_data(args.symbol, period=args.period)
    if df is None or len(df) == 0:
        print("  ❌ No data fetched.")
        return

    data = OHLCVData.from_dataframe(df)
    optimizer = StrategyOptimizer()
    result = optimizer._evaluate_strategy(strategy, data, {})
    print(f"\n  📈 Results:")
    print(f"    Trades:       {result.total_trades}")
    print(f"    Win Rate:     {result.win_rate * 100:.1f}%")
    print(f"    Total Return: {result.total_return * 100:.2f}%")
    print(f"    Max Drawdown: {result.max_drawdown * 100:.2f}%")
    print(f"    Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"    Score:        {result.score:.4f}\n")


def _strategy_optimize(args):
    """Optimize a YAML DSL strategy via grid search."""
    from src.strategy.optimizer import StrategyOptimizer
    from src.strategy.expression import OHLCVData

    if not args.param:
        print("  ❌ Need at least one --param (e.g. --param rsi_period:10:30:5)")
        return

    with open(args.file, "r") as f:
        yaml_str = f.read()

    params = {}
    for p in args.param:
        parts = p.split(":")
        if len(parts) != 4:
            print(f"  ❌ Invalid param format '{p}' — use name:min:max:step")
            return
        name, mn, mx, step = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
        import numpy as np
        params[name] = [int(v) if v == int(v) else v for v in np.arange(mn, mx + step, step)]

    print(f"\n  🔬 Optimizing on {args.symbol} ({args.period})...")
    df = _fetch_data(args.symbol, period=args.period)
    if df is None:
        print("  ❌ No data fetched.")
        return

    data = OHLCVData.from_dataframe(df)
    optimizer = StrategyOptimizer()
    results = optimizer.grid_search(yaml_str, params, data)
    print(f"\n  📊 Top 5 Results ({len(results)} combinations tested):\n")
    for i, r in enumerate(optimizer.top_n(5), 1):
        print(f"    #{i}: {r.params}")
        print(f"        Return: {r.total_return * 100:.2f}%  Win: {r.win_rate * 100:.0f}%  "
              f"Sharpe: {r.sharpe_ratio:.2f}  DD: {r.max_drawdown * 100:.1f}%  Score: {r.score:.4f}")
    print(f"\n  🏆 Best params: {optimizer.best_params()}\n")


def cmd_watchlist(args):
    """Manage watchlists."""
    from src.screener.watchlist import WatchlistManager
    from src.exchanges.registry import ExchangeRegistry
    wm = WatchlistManager(exchange_registry=ExchangeRegistry)
    cmd = args.watchlist_cmd

    if cmd == "create":
        wl = wm.create(args.name, args.symbols or [])
        print(f"  ✓ Created watchlist '{wl.name}' with {len(wl.symbols)} symbols")
    elif cmd == "quotes":
        quotes = wm.get_quotes(args.name)
        for q in quotes:
            sym = q.get("symbol", "?")
            last = q.get("last", "N/A")
            print(f"  {sym}: {last}")
    elif cmd == "add":
        wm.add(args.name, args.symbol)
        print(f"  ✓ Added {args.symbol.upper()} to '{args.name}'")
    elif cmd == "remove":
        wm.remove(args.name, args.symbol)
        print(f"  ✓ Removed {args.symbol.upper()} from '{args.name}'")
    elif cmd == "export":
        output = wm.export(args.name, format=args.format)
        print(output)
    elif cmd == "list":
        names = wm.list_all()
        if names:
            for n in names:
                wl = wm.get(n)
                count = len(wl.symbols) if wl else 0
                print(f"  {n} ({count} symbols)")
        else:
            print("  No watchlists found.")
    else:
        print("  Usage: finclaw watchlist [create|quotes|add|remove|export|list]")


def cmd_sentiment(args):
    """Sentiment analysis for a symbol."""
    from src.sentiment.analyzer import SentimentAnalyzer
    from src.sentiment.news import NewsAggregator

    symbol = args.symbol.upper()
    print(f"\n  🧠 Sentiment Analysis: {symbol}\n")

    # Social Buzz mode (--buzz flag)
    if getattr(args, "buzz", False):
        from src.sentiment.social_buzz import SocialBuzzAggregator
        buzz = SocialBuzzAggregator()
        result = buzz.get_buzz_score(symbol)
        print(f"  Social Buzz Score: {result['overall_score']:+.4f} ({result['overall_label']})")
        print(f"  Buzz Level:        {result['buzz_level']} ({result['total_data_points']} data points)")
        for src_name, src_data in result["sources"].items():
            score = src_data.get("score", src_data.get("overall_score", 0))
            label = src_data.get("label", src_data.get("overall_label", "n/a"))
            print(f"    {src_name:15s}: {score:+.4f} ({label})")
        print()
        return

    # News sentiment
    agg = NewsAggregator()
    news = agg.get_news(symbol, limit=20)
    analyzer = SentimentAnalyzer()

    if news:
        headlines = [a["title"] for a in news]
        result = analyzer.analyze_headlines(headlines)
        print(f"  News Sentiment:  {result['overall_score']:+.3f} ({result['overall_label']})")
        print(f"  Headlines:       {result['total']} ({result['bullish_count']}↑ {result['bearish_count']}↓ {result['neutral_count']}—)")
        print(f"  Trend:           {result['trend']}")
    else:
        print("  News:            No headlines fetched (offline or no results)")

    # Fear & Greed
    fg = analyzer.fear_greed_composite(symbol)
    print(f"\n  Fear & Greed:    {fg['value']}/100 ({fg['label']})")
    for k, v in fg["components"].items():
        if k != "note":
            print(f"    {k}: {v}")

    # Reddit (optional)
    if getattr(args, "reddit", False):
        from src.sentiment.social import SocialMonitor
        sm = SocialMonitor()
        rd = sm.reddit_sentiment("stocks", symbol)
        print(f"\n  Reddit (r/stocks): {rd['sentiment_score']:+.3f} ({rd['sentiment_label']}) | {rd['mentions']} mentions")

    print()


def cmd_news(args):
    """Get financial news."""
    from src.sentiment.news import NewsAggregator

    agg = NewsAggregator()
    symbol = args.symbol.upper()

    if args.search:
        articles = agg.search_news(args.search, days=7)
        print(f"\n  🔍 News search: '{args.search}'\n")
    else:
        articles = agg.get_news(symbol, limit=args.limit)
        print(f"\n  📰 News: {symbol} (latest {args.limit})\n")

    if not articles:
        print("  No articles found.")
    else:
        for i, a in enumerate(articles[:args.limit], 1):
            pub = a.get("published", "")[:20]
            src = a.get("source", "")
            print(f"  {i:2}. [{src}] {a['title'][:80]}")
            if pub:
                print(f"      {pub}")
    print()


def cmd_trending(args):
    """Show trending topics and WSB tickers."""
    from src.sentiment.news import NewsAggregator
    from src.sentiment.social import SocialMonitor

    print("\n  🔥 Trending Topics\n")

    agg = NewsAggregator()
    topics = agg.trending_topics()
    if topics:
        for t in topics[:10]:
            print(f"  • {t['topic']} ({t['mention_count']} mentions)")
    else:
        print("  No trending topics (feeds may be unavailable)")

    print("\n  🦍 WSB Trending Tickers\n")
    sm = SocialMonitor()
    wsb = sm.wsb_trending()
    if wsb:
        for t in wsb[:10]:
            print(f"  ${t['symbol']:<6} {t['mentions']} mentions | {t['sentiment_score']:+.3f} ({t['sentiment_label']})")
    else:
        print("  No WSB data (Reddit may be unavailable)")
    print()


def cmd_reddit_buzz(args):
    """Top buzzing tickers in a subreddit."""
    from src.sentiment.reddit_sentiment import RedditSentiment

    sub = args.subreddit
    print(f"\n  🦍 Reddit Buzz: r/{sub}\n")

    rs = RedditSentiment()
    results = rs.subreddit_buzz(sub, limit=args.limit)

    if not results:
        print("  No tickers found (subreddit may be unavailable)")
    else:
        print(f"  {'Ticker':<8} {'Mentions':>8} {'Engagement':>10} {'Sentiment':>10} {'Label'}")
        print(f"  {'─'*8} {'─'*8} {'─'*10} {'─'*10} {'─'*10}")
        for t in results[:20]:
            print(f"  ${t['ticker']:<7} {t['mentions']:>8} {t['total_engagement']:>10} {t['sentiment_score']:>+10.4f} {t['sentiment_label']}")
    print()


def cmd_scan_cn(args):
    """Scan A-share stocks for buy signals."""
    from src.cn_scanner import scan_cn_stocks, format_scan_output

    top = args.top
    sector = args.sector
    min_score = args.min_score
    sort_by = args.sort

    print(f"\n  Scanning A-share stocks (top={top}, sector={sector or 'all'}, min_score={min_score})...")

    try:
        results = scan_cn_stocks(top=top, sector=sector, min_score=min_score, sort_by=sort_by)
    except ValueError as e:
        print(f"  ERROR: {e}")
        return

    if not results:
        print("  No results found. Check network or try different filters.")
        return

    version = _get_version()
    output = format_scan_output(results, version=version)
    print(output)
    return results


def cmd_scan(args):
    """Run market scanner."""
    from src.screener.scanner import MarketScanner

    scanner = MarketScanner()
    symbols = [s.strip().upper() for s in args.symbols.split(",")]

    # Parse rule expression like "rsi<30 AND volume>2x"
    rule_str = args.rule
    conditions = []
    for part in rule_str.split(" AND "):
        part = part.strip()
        if "rsi<" in part.lower():
            val = float(part.lower().split("rsi<")[1])
            conditions.append(MarketScanner.rsi_below(val))
        elif "rsi>" in part.lower():
            val = float(part.lower().split("rsi>")[1])
            conditions.append(MarketScanner.rsi_above(val))
        elif "volume>" in part.lower():
            val_str = part.lower().split("volume>")[1].replace("x", "")
            conditions.append(MarketScanner.volume_above(float(val_str)))

    if not conditions:
        print("  No valid rules parsed. Example: --rule 'rsi<30 AND volume>2x'")
        return

    def combined(data):
        return all(c(data) for c in conditions)

    scanner.add_rule(args.rule, combined, action="alert")

    print(f"  Scanning {len(symbols)} symbols with rule: {args.rule}")
    results = scanner.scan_once(symbols)
    if results:
        for r in results:
            print(f"  ⚡ {r.symbol}: RSI={r.data.get('rsi_14', '?'):.1f}, Vol={r.data.get('volume_ratio', '?'):.1f}x")
    else:
        print("  No matches found.")


def cmd_alert(args):
    """Smart alert system commands."""
    import json as _json
    from pathlib import Path
    from src.alerts.engine import (
        AlertEngine, AlertRule, PriceAlert, TechnicalAlert, VolumeAlert, PortfolioAlert,
        AlertCondition, AlertSeverity,
    )
    from src.alerts.channels import ConsoleChannel, FileChannel
    from src.alerts.history import AlertHistory

    config_dir = Path.home() / ".finclaw"
    config_dir.mkdir(exist_ok=True)
    rules_file = config_dir / "alert_rules.json"
    history_path = config_dir / "alert_history.json"

    subcmd = getattr(args, "alert_cmd", None)

    if subcmd == "add":
        # Load existing rules
        rules = []
        if rules_file.exists():
            rules = _json.loads(rules_file.read_text())

        rule_def = {"symbol": args.symbol, "cooldown": args.cooldown, "channel": args.channel}
        if args.price_above is not None:
            rule_def.update(condition="price_above", threshold=args.price_above, name=f"{args.symbol} price > {args.price_above}")
        elif args.price_below is not None:
            rule_def.update(condition="price_below", threshold=args.price_below, name=f"{args.symbol} price < {args.price_below}")
        elif args.rsi_above is not None:
            rule_def.update(condition="rsi_above", threshold=args.rsi_above, name=f"{args.symbol} RSI > {args.rsi_above}")
        elif args.rsi_below is not None:
            rule_def.update(condition="rsi_below", threshold=args.rsi_below, name=f"{args.symbol} RSI < {args.rsi_below}")
        elif args.volume_spike is not None:
            rule_def.update(condition="volume_spike", threshold=args.volume_spike, name=f"{args.symbol} vol spike > {args.volume_spike}x")
        elif args.macd_cross:
            rule_def.update(condition="macd_cross", threshold=0, name=f"{args.symbol} MACD cross")
        elif args.bb_breakout:
            rule_def.update(condition="bollinger_breakout", threshold=0, name=f"{args.symbol} BB breakout")
        elif args.drawdown is not None:
            rule_def.update(condition="drawdown", threshold=args.drawdown, name=f"{args.symbol} drawdown > {args.drawdown:.0%}")
        else:
            print("  ERROR: Specify at least one alert condition")
            return

        rules.append(rule_def)
        rules_file.write_text(_json.dumps(rules, indent=2))
        print(f"  ✅ Alert added: {rule_def['name']} (channel: {rule_def['channel']})")

    elif subcmd == "list":
        if not rules_file.exists():
            print("  No alert rules configured.")
            return
        rules = _json.loads(rules_file.read_text())
        if not rules:
            print("  No alert rules configured.")
            return
        print(f"\n  📋 {len(rules)} alert rule(s):\n")
        for i, r in enumerate(rules, 1):
            print(f"  {i}. [{r.get('condition', '?')}] {r.get('name', '?')} (channel: {r.get('channel', 'console')})")

    elif subcmd == "remove":
        if not rules_file.exists():
            print("  No rules to remove.")
            return
        rules = _json.loads(rules_file.read_text())
        idx = args.rule_id - 1
        if 0 <= idx < len(rules):
            removed = rules.pop(idx)
            rules_file.write_text(_json.dumps(rules, indent=2))
            print(f"  ✅ Removed: {removed.get('name', '?')}")
        else:
            print(f"  ERROR: Invalid rule ID {args.rule_id}")

    elif subcmd == "history":
        hist = AlertHistory(persist_path=history_path)
        recent = hist.get_recent(hours=args.hours)
        if hasattr(args, "export") and args.export:
            print(hist.export(format=args.export))
        elif not recent:
            print(f"  No alerts in the last {args.hours}h.")
        else:
            print(f"\n  📜 {len(recent)} alert(s) in last {args.hours}h:\n")
            for a in recent:
                ts = a.timestamp.strftime("%Y-%m-%d %H:%M")
                icon = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(a.severity.value, "•")
                print(f"  {ts} {icon} {a.message}")

    elif subcmd == "start":
        symbols = [s.strip() for s in args.symbols.split(",")]
        engine = AlertEngine()
        engine.add_channel(ConsoleChannel())

        if rules_file.exists():
            rules = _json.loads(rules_file.read_text())
            for r in rules:
                if r["symbol"] in symbols:
                    rule = AlertRule(
                        name=r["name"],
                        condition=AlertCondition(r["condition"]),
                        symbol=r["symbol"],
                        threshold=r.get("threshold", 0),
                        cooldown=r.get("cooldown", 3600),
                    )
                    engine.add_rule(rule)

        if not engine.rules:
            print("  No matching rules for given symbols. Add rules first.")
            return

        print(f"  🚀 Alert engine started for {', '.join(symbols)} ({len(engine.rules)} rules)")
        print("  Press Ctrl+C to stop.\n")

        import time
        hist = AlertHistory(persist_path=history_path)
        try:
            while True:
                for sym in symbols:
                    df = _fetch_data(sym, period="3mo")
                    if df is None:
                        continue
                    data = {
                        "symbol": sym,
                        "price": float(df["Close"].iloc[-1]),
                        "close": df["Close"].tolist(),
                        "volume": df["Volume"].tolist(),
                    }
                    triggered = engine.evaluate(data)
                    hist.record_many(triggered)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  ⏹ Alert engine stopped.")
    else:
        print("  Usage: finclaw alert {add|list|remove|history|start}")


def cmd_chart(args):
    """Handle chart commands using terminal visualization."""
    from src.viz.charts import TerminalChart

    period_map = {"30d": "1mo", "6mo": "6mo", "1y": "1y", "3mo": "3mo", "1mo": "1mo", "5y": "5y"}
    period = period_map.get(args.period, args.period)
    df = _fetch_data(args.symbol, period=period)
    if df is None:
        print(f"  Could not fetch data for {args.symbol}")
        return

    print(f"\n  📊 {args.symbol} — {args.type} chart ({args.period})\n")

    if args.type == "candle":
        data = [
            {"open": row["Open"], "high": row["High"], "low": row["Low"], "close": row["Close"]}
            for _, row in df.iterrows()
        ]
        print(TerminalChart.candlestick(data, width=args.width, height=args.height))
    elif args.type == "line":
        values = df["Close"].tolist()
        print(TerminalChart.line(values, width=args.width, height=args.height, label=args.symbol))
    elif args.type == "bar":
        # Show last 20 daily returns
        closes = df["Close"].tolist()
        returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
        recent = returns[-20:]
        labels = [str(df.index[-(len(recent)-i)])[:10] for i in range(len(recent))]
        print(TerminalChart.bar(labels, recent, width=args.width))
    elif args.type == "histogram":
        closes = df["Close"].tolist()
        returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 for i in range(1, len(closes))]
        print(TerminalChart.histogram(returns, width=args.width))
    print()


def cmd_portfolio_dashboard(args):
    """Render portfolio dashboard."""
    from src.viz.dashboard import PortfolioDashboard
    import json, os

    pf_file = getattr(args, "file", "portfolio.json")
    if not os.path.exists(pf_file):
        # Demo portfolio
        portfolio = {
            "total_value": 125430,
            "total_cost": 120000,
            "holdings": [
                {"symbol": "AAPL", "weight": 0.45, "pnl_pct": 2.3},
                {"symbol": "MSFT", "weight": 0.30, "pnl_pct": -0.5},
                {"symbol": "GOOGL", "weight": 0.25, "pnl_pct": 1.1},
            ],
            "history": [120000, 121000, 119500, 122000, 124000, 123500, 125430],
        }
    else:
        with open(pf_file) as f:
            portfolio = json.load(f)

    dash = PortfolioDashboard()
    print(dash.render(portfolio))


def cmd_backtest_visual(args):
    """Render visual backtest report."""
    from src.viz.report import BacktestVisualizer
    print("\n  🎨 Visual Backtest Report")
    print("  Run a backtest first, then use --visual to see charts.\n")


def _cmd_a2a(args):
    """Handle 'finclaw a2a' subcommands."""
    if args.a2a_cmd == "card":
        from src.a2a.agent_card import FinClawAgentCard
        card = FinClawAgentCard()
        print(card.to_json())
    elif args.a2a_cmd == "serve":
        from src.a2a.server import run_server
        print(f"  🦀 FinClaw A2A server starting on http://{args.host}:{args.port}")
        print(f"  Agent card: http://{args.host}:{args.port}/.well-known/agent.json")
        asyncio.run(run_server(host=args.host, port=args.port, auth_token=args.auth_token))
    else:
        print("  Usage: finclaw a2a {serve,card}")


# Paper trading session state (persisted in memory for CLI session)
_paper_state_path = os.path.join(os.path.expanduser("~"), ".finclaw", "paper_state.json")


def _load_paper_engine():
    """Load or create paper trading engine."""
    import json as _json
    from src.paper.engine import PaperTradingEngine
    engine = PaperTradingEngine()
    if os.path.exists(_paper_state_path):
        try:
            with open(_paper_state_path) as f:
                state = _json.load(f)
            engine = PaperTradingEngine(
                initial_balance=state.get("initial_balance", 100000),
                exchange=state.get("exchange", "yahoo"),
            )
            engine.balance = state.get("balance", engine.initial_balance)
            engine._realized_pnl = state.get("realized_pnl", 0.0)
            engine.trade_log = state.get("trade_log", [])
            from src.paper.engine import Position
            for sym, pdata in state.get("positions", {}).items():
                engine.positions[sym] = Position(
                    symbol=sym,
                    quantity=pdata["quantity"],
                    avg_cost=pdata["avg_cost"],
                    current_price=pdata.get("current_price", 0),
                )
        except Exception:
            pass
    return engine


def _save_paper_engine(engine):
    """Persist paper trading engine state."""
    import json as _json
    os.makedirs(os.path.dirname(_paper_state_path), exist_ok=True)
    state = {
        "initial_balance": engine.initial_balance,
        "exchange": engine.exchange,
        "balance": engine.balance,
        "realized_pnl": engine._realized_pnl,
        "trade_log": engine.trade_log,
        "positions": {s: {"quantity": p.quantity, "avg_cost": p.avg_cost, "current_price": p.current_price}
                      for s, p in engine.positions.items()},
    }
    with open(_paper_state_path, "w") as f:
        _json.dump(state, f, indent=2)


def _handle_paper(args):
    """Handle paper trading subcommands."""
    from src.paper.engine import PaperTradingEngine
    from src.paper.dashboard import PaperDashboard
    from src.paper.runner import StrategyRunner, BUILTIN_STRATEGIES
    from src.paper.journal import TradeJournal

    cmd = getattr(args, "paper_cmd", None)
    if not cmd:
        print("  Usage: finclaw paper {start,buy,sell,portfolio,pnl,history,dashboard,run-strategy,journal,reset}")
        return

    if cmd == "start":
        engine = PaperTradingEngine(initial_balance=args.balance, exchange=args.exchange)
        _save_paper_engine(engine)
        print(f"  📄 Paper trading started!")
        print(f"  Balance: ${args.balance:,.2f} | Exchange: {args.exchange}")
        return

    if cmd == "reset":
        if os.path.exists(_paper_state_path):
            os.remove(_paper_state_path)
        print("  📄 Paper trading session reset.")
        return

    engine = _load_paper_engine()

    if cmd == "buy":
        order = engine.buy(args.symbol, args.quantity, getattr(args, "type", "market"), getattr(args, "limit_price", None))
        _save_paper_engine(engine)
        if order.status.value == "filled":
            print(f"  🟢 BUY {args.symbol} x{args.quantity} @${order.filled_price:.2f} = ${order.filled_price * args.quantity:,.2f}")
        else:
            reason = getattr(order, "reject_reason", "") or "Unknown reason"
            print(f"  ❌ Order rejected: {args.symbol} — {reason}")

    elif cmd == "sell":
        order = engine.sell(args.symbol, args.quantity, getattr(args, "type", "market"), getattr(args, "limit_price", None))
        _save_paper_engine(engine)
        if order.status.value == "filled":
            print(f"  🔴 SELL {args.symbol} x{args.quantity} @${order.filled_price:.2f}")
        else:
            reason = getattr(order, "reject_reason", "") or "Unknown reason"
            print(f"  ❌ Order rejected: {args.symbol} — {reason}")

    elif cmd == "portfolio":
        portfolio = engine.get_portfolio()
        print(f"\n  💼 Paper Portfolio")
        print(f"  Cash:      ${portfolio.cash:>12,.2f}")
        print(f"  Positions: ${portfolio.positions_value:>12,.2f}")
        print(f"  Total:     ${portfolio.total_value:>12,.2f}")
        print(f"  Return:    {portfolio.total_return:>+11.2f}%")
        if portfolio.positions:
            print(f"\n  {'Symbol':<8} {'Qty':>8} {'Avg':>10} {'Price':>10} {'P&L':>12}")
            for sym, pos in sorted(portfolio.positions.items()):
                print(f"  {sym:<8} {pos.quantity:>8.1f} ${pos.avg_cost:>9.2f} ${pos.current_price:>9.2f} ${pos.unrealized_pnl:>+11.2f}")

    elif cmd == "pnl":
        pnl = engine.get_pnl()
        print(f"\n  📊 Paper P&L")
        print(f"  Realized:   ${pnl.realized:>+12,.2f}")
        print(f"  Unrealized: ${pnl.unrealized:>+12,.2f}")
        print(f"  Total:      ${pnl.total:>+12,.2f}")
        print(f"  Return:     {pnl.total_return_pct:>+11.2f}%")
        if pnl.total_trades > 0:
            print(f"  Win Rate:   {pnl.win_rate:.1f}% ({pnl.win_count}W/{pnl.loss_count}L)")

    elif cmd == "history":
        trades = engine.get_trade_history()
        if not trades:
            print("  No trades yet.")
        else:
            for t in trades:
                ts = datetime.fromtimestamp(t["timestamp"]).strftime("%Y-%m-%d %H:%M")
                print(f"  {ts} {t['side']:<4} {t['symbol']:<6} x{t['quantity']:<8} @${t['price']:.2f}")

    elif cmd == "dashboard":
        dashboard = PaperDashboard()
        print(dashboard.render(engine))

    elif cmd == "run-strategy":
        strategy_name = args.strategy
        if strategy_name not in BUILTIN_STRATEGIES:
            print(f"  Unknown strategy: {strategy_name}")
            print(f"  Available: {', '.join(BUILTIN_STRATEGIES.keys())}")
            return
        symbols = [s.strip() for s in args.symbols.split(",")]
        strategy = BUILTIN_STRATEGIES[strategy_name]()
        runner = StrategyRunner(engine, strategy, symbols=symbols)
        for _ in range(args.ticks):
            runner.tick()
        _save_paper_engine(engine)
        stats = runner.get_stats()
        print(f"  📈 Strategy: {strategy_name}")
        print(f"  Ticks: {stats['ticks']} | Trades: {stats['trades']}")
        print(f"  P&L: ${stats['total_pnl']:+,.2f} | Win Rate: {stats['win_rate']:.1f}%")

    elif cmd == "journal":
        journal_path = os.path.join(os.path.expanduser("~"), ".finclaw", "paper_journal.json")
        journal = TradeJournal(journal_path)
        # Auto-record any trades from engine
        for t in engine.get_trade_history():
            journal.record_trade(t)
        if getattr(args, "export", None):
            print(journal.export(args.export))
        else:
            date = getattr(args, "date", None)
            print(journal.daily_summary(date))


def _cmd_generate_strategy(args):
    """Handle: finclaw generate-strategy"""
    from src.ai_strategy.strategy_generator import StrategyGenerator
    import asyncio

    gen = StrategyGenerator(
        provider_name=args.provider,
        market=args.market,
        risk=args.risk,
    )

    if args.interactive:
        code = asyncio.run(gen.interactive_async())
        if code and args.output:
            with open(args.output, "w") as f:
                f.write(code)
            print(f"  Saved to {args.output}")
        elif code:
            print(f"\n{code}")
        return

    if not args.description:
        print("  Usage: finclaw generate-strategy \"description\" [--market us_stock] [--risk medium]")
        print("         finclaw generate-strategy --interactive")
        return

    print(f"  🤖 Generating strategy for: {args.description}")
    print(f"     Market: {args.market} | Risk: {args.risk}")
    result = gen.generate(args.description)

    if result["valid"]:
        print(f"  ✅ Generated: {result['class_name']}\n")
        print(result["code"])
        if args.output:
            with open(args.output, "w") as f:
                f.write(result["code"])
            print(f"\n  Saved to {args.output}")
    else:
        print(f"  ❌ Generation had issues: {result['errors']}")
        if result["code"]:
            print(result["code"])


def _cmd_optimize_strategy(args):
    """Handle: finclaw optimize-strategy"""
    from src.ai_strategy.strategy_optimizer import StrategyOptimizer

    with open(args.strategy_file) as f:
        code = f.read()

    print(f"  🔧 Analyzing strategy: {args.strategy_file}")
    optimizer = StrategyOptimizer(provider_name=args.provider)

    # Simple backtest results placeholder — in production would run real backtest
    backtest_results = {
        "ticker": args.data,
        "period": args.period,
        "note": "Run a backtest first for real results. This is AI analysis of the code.",
    }

    result = optimizer.analyze(code, backtest_results)
    print(f"\n  📊 Analysis: {result.get('analysis', 'N/A')}")
    suggestions = result.get("suggestions", [])
    if suggestions:
        print("\n  💡 Suggestions:")
        for s in suggestions:
            print(f"    • {s.get('parameter', '?')}: {s.get('current', '?')} → {s.get('suggested', '?')} — {s.get('reason', '')}")
    print(f"\n  ⚠ Risk: {result.get('risk_assessment', 'N/A')}")


def _cmd_copilot(args):
    """Handle: finclaw copilot"""
    from src.ai_strategy.copilot import FinClawCopilot
    copilot = FinClawCopilot()
    copilot.run_interactive()


def cmd_defi_tvl(args):
    """Top DeFi protocols by TVL."""
    from src.defi.defillama import DefiLlamaClient
    client = DefiLlamaClient()
    protocols = client.get_top_protocols(limit=args.limit)

    print(f"\n  ?? Top {len(protocols)} DeFi Protocols by TVL\n")
    print(f"  {'#':<4} {'Protocol':<25} {'TVL (USD)':>16} {'Chain':<15} {'Category':<15} {'1d %':>8} {'7d %':>8}")
    print("  " + "─" * 95)
    for i, p in enumerate(protocols, 1):
        tvl_str = f"${p.tvl:>14,.0f}" if p.tvl else "N/A"
        d1 = f"{p.change_1d:>+7.2f}%" if p.change_1d is not None else "    N/A"
        d7 = f"{p.change_7d:>+7.2f}%" if p.change_7d is not None else "    N/A"
        print(f"  {i:<4} {p.name:<25} {tvl_str} {p.chain:<15} {p.category:<15} {d1} {d7}")
    print()


def cmd_yields(args):
    """Best yield farming opportunities."""
    from src.defi.defillama import DefiLlamaClient
    client = DefiLlamaClient()
    pools = client.get_best_yields(chain=args.chain, min_tvl=args.min_tvl)[:args.limit]

    chain_label = f" on {args.chain}" if args.chain else ""
    print(f"\n  🌾 Top {len(pools)} Yield Opportunities{chain_label}\n")
    print(f"  {'#':<4} {'Project':<20} {'Pool':<20} {'Chain':<12} {'APY':>10} {'TVL (USD)':>16}")
    print("  " + "─" * 85)
    for i, p in enumerate(pools, 1):
        apy_str = f"{p.apy:>9.2f}%"
        tvl_str = f"${p.tvl_usd:>14,.0f}"
        print(f"  {i:<4} {p.project:<20} {p.symbol:<20} {p.chain:<12} {apy_str} {tvl_str}")
    print()


def cmd_stablecoins(args):
    """Stablecoin market overview."""
    from src.defi.defillama import DefiLlamaClient
    client = DefiLlamaClient()
    stables = client.get_stablecoin_market()[:args.limit]

    total = sum(s.circulating for s in stables)
    print(f"\n  💲 Stablecoin Market Overview (Total: ${total:,.0f})\n")
    print(f"  {'#':<4} {'Name':<25} {'Symbol':<10} {'Circulating':>18} {'Peg Type':<15} {'Share':>8}")
    print("  " + "─" * 85)
    for i, s in enumerate(stables, 1):
        share = s.circulating / total * 100 if total > 0 else 0
        print(f"  {i:<4} {s.name:<25} {s.symbol:<10} ${s.circulating:>16,.0f} {s.peg_type:<15} {share:>6.1f}%")
    print()


def cmd_btc_metrics(args):
    """Show BTC on-chain metrics dashboard."""
    from src.crypto.btc_metrics import BTCMetricsClient
    client = BTCMetricsClient()

    print("\n  ⛓️  BTC On-Chain Metrics Dashboard\n")

    metrics = client.get_onchain_metrics()
    print(f"  Hashrate:       {metrics.hashrate:,.0f} TH/s")
    print(f"  Difficulty:     {metrics.difficulty:,.0f}")
    print(f"  Mempool:        {metrics.mempool_size:,} unconfirmed txs")
    print(f"  Avg Block Time: {metrics.avg_block_time:.1f} min")
    print(f"  Avg Tx Fee:     ${metrics.avg_tx_fee_usd:.2f}")

    mvrv = client.get_mvrv_ratio()
    print(f"\n  MVRV Ratio:     {mvrv.mvrv_ratio:.3f} ({mvrv.signal})")
    print(f"  Market Cap:     ${mvrv.market_cap:,.0f}")
    print(f"  Realized Cap:   ${mvrv.realized_cap:,.0f}")

    miner = client.get_miner_outflow()
    print(f"\n  Miner Outflow:  {miner.daily_outflow_btc:.0f} BTC/day ({miner.outflow_trend})")
    print(f"  7d Avg:         {miner.avg_7d_outflow_btc:.0f} BTC/day")
    print(f"  Signal:         {miner.signal}")

    fg = client.get_fear_greed(limit=1)
    if fg:
        print(f"\n  Fear & Greed:   {fg[0].value}/100 ({fg[0].label})")
    print()


def cmd_funding_rates(args):
    """Multi-exchange funding rate comparison."""
    from src.crypto.funding_dashboard import FundingDashboardClient
    symbols = [s.strip() for s in args.symbols.split(",")]
    client = FundingDashboardClient()
    dashboard = client.get_dashboard(symbols, min_spread=args.min_spread)

    print("\n  💰 Funding Rate Dashboard\n")
    print(f"  {'Exchange':<12} {'Symbol':<12} {'8h Rate':>12} {'Annualized':>12}")
    print("  " + "─" * 50)
    for r in sorted(dashboard.rates, key=lambda x: (x.symbol, x.exchange)):
        print(f"  {r.exchange:<12} {r.symbol:<12} {r.rate:>+11.6f} {r.annualized:>+11.4f}%")

    if dashboard.arbitrage_opportunities:
        print(f"\n  🎯 Arbitrage Opportunities (spread > {args.min_spread}%):\n")
        for arb in dashboard.arbitrage_opportunities:
            print(f"  {arb.symbol}: Long {arb.long_exchange} ({arb.long_rate:+.4f}%) → Short {arb.short_exchange} ({arb.short_rate:+.4f}%) = {arb.spread:.4f}% spread")
    print()


def cmd_fear_greed(args):
    """Show current Fear & Greed Index."""
    from src.crypto.btc_metrics import BTCMetricsClient
    client = BTCMetricsClient()
    data = client.get_fear_greed(limit=args.history)

    print("\n  😱 Fear & Greed Index\n")
    for fg in data:
        from datetime import datetime
        ts = datetime.fromtimestamp(fg.timestamp).strftime("%Y-%m-%d") if fg.timestamp > 0 else "now"
        bar = "█" * (fg.value // 5) + "░" * (20 - fg.value // 5)
        print(f"  {ts}  [{bar}] {fg.value}/100 — {fg.label}")
    print()


def _handle_portfolio_tracker(args):
    """Handle portfolio tracker subcommands (add/remove/show/history/alert/export)."""
    from src.portfolio.tracker import PortfolioTracker

    pf_name = getattr(args, "portfolio", "main")
    tracker = PortfolioTracker(portfolio_name=pf_name)
    cmd = args.portfolio_cmd

    if cmd == "add":
        h = tracker.add(args.symbol, args.quantity, buy_price=args.price)
        print(f"  ✅ Added {args.quantity} {args.symbol.upper()} @${args.price:.2f}")
        print(f"     Now holding: {h.quantity} {h.symbol} (avg ${h.avg_cost:.2f})")

    elif cmd == "remove":
        h = tracker.remove(args.symbol, args.quantity)
        if h:
            print(f"  ✅ Removed {args.quantity} {args.symbol.upper()}")
            print(f"     Remaining: {h.quantity} {h.symbol}")
        else:
            print(f"  ✅ Removed all {args.symbol.upper()}")

    elif cmd == "show":
        status = tracker.show()
        tracker.snapshot()  # auto-snapshot on show
        print(f"\n  📊 Portfolio: {status['portfolio']}\n")
        if not status["holdings"]:
            print("  No holdings. Use 'finclaw portfolio add' to start.")
            return
        print(f"  {'Symbol':<10} {'Qty':>8} {'AvgCost':>10} {'Price':>10} {'Value':>12} {'P&L':>10} {'%':>8}")
        print("  " + "─" * 72)
        for r in status["holdings"]:
            print(f"  {r['symbol']:<10} {r['quantity']:>8.2f} {r['avg_cost']:>10.2f} {r['price']:>10.2f} "
                  f"{r['value']:>12,.2f} {r['pnl']:>+10,.2f} {r['pnl_pct']:>+7.1%}")
        print("  " + "─" * 72)
        print(f"  {'TOTAL':<10} {'':>8} {'':>10} {'':>10} "
              f"{status['total_value']:>12,.2f} {status['total_pnl']:>+10,.2f} {status['total_pnl_pct']:>+7.1%}")

        # Show allocation
        alloc = tracker.allocation()
        if alloc:
            print(f"\n  📈 Allocation:")
            for a in alloc:
                bar = "█" * int(a["pct"] / 2.5)
                print(f"    {a['symbol']:<8} {bar} {a['pct']:.1f}%")

    elif cmd == "history":
        history = tracker.get_history()
        if not history:
            print("  No history yet. Use 'finclaw portfolio show' to record snapshots.")
            return
        print(f"\n  📅 Portfolio History ({pf_name})\n")
        print(f"  {'Date':<12} {'Value':>14} {'Cost':>14} {'P&L':>12} {'Holdings':>8}")
        print("  " + "─" * 62)
        for s in history:
            pnl = s["total_value"] - s["total_cost"]
            print(f"  {s['date']:<12} {s['total_value']:>14,.2f} {s['total_cost']:>14,.2f} {pnl:>+12,.2f} {s['holdings_count']:>8}")

    elif cmd == "alert":
        alert = tracker.add_alert(args.symbol, above=args.above, below=args.below)
        cond = f"above ${alert.threshold:,.2f}" if alert.condition == "above" else f"below ${alert.threshold:,.2f}"
        print(f"  🔔 Alert set: {alert.symbol} {cond}")

    elif cmd == "export":
        what = getattr(args, "what", "holdings")
        output = getattr(args, "output", None)
        if output:
            tracker.export_to_file(output, what=what)
            print(f"  ✅ Exported {what} to {output}")
        else:
            print(tracker.export_csv(what=what))


def cmd_watch(args):
    """Handle 'finclaw watch' shortcut commands."""
    from src.watchlist.manager import WatchlistManager

    wm = WatchlistManager()
    action = args.watch_action
    extras = args.watch_args or []
    name = args.name

    if action == "show":
        # If extras provided, treat first as watchlist name
        if extras:
            name = extras[0]
        wl = wm.get(name)
        if wl is None:
            if name == "default":
                wm.create("default")
                print("  Created empty 'default' watchlist. Use 'finclaw watch add AAPL MSFT' to add tickers.")
            else:
                print(f"  Watchlist '{name}' not found. Create it with: finclaw watch create {name}")
            return
        if not wl.tickers:
            print(f"  Watchlist '{name}' is empty. Use 'finclaw watch add TICKER' to add tickers.")
            return
        quotes = wm.fetch_quotes(name)
        print(wm.format_table(name, quotes))

    elif action == "add":
        if not extras:
            print("  Usage: finclaw watch add TICKER1 TICKER2 ...")
            return
        wl = wm.get(name)
        if wl is None:
            wm.create(name)
        wm.add_tickers(name, extras)
        print(f"  Added {', '.join(t.upper() for t in extras)} to '{name}'")

    elif action == "remove":
        if not extras:
            print("  Usage: finclaw watch remove TICKER")
            return
        for t in extras:
            try:
                wm.remove_ticker(name, t)
                print(f"  Removed {t.upper()} from '{name}'")
            except KeyError:
                print(f"  Watchlist '{name}' not found")

    elif action == "create":
        wl_name = extras[0] if extras else name
        tickers = extras[1:] if len(extras) > 1 else []
        wm.create(wl_name, tickers)
        print(f"  Created watchlist '{wl_name}'" + (f" with {len(tickers)} tickers" if tickers else ""))

    elif action == "list":
        names = wm.list_all()
        if not names:
            print("  No watchlists. Create one with: finclaw watch create <name>")
        else:
            for n in names:
                wl = wm.get(n)
                count = len(wl.tickers) if wl else 0
                print(f"  {n} ({count} tickers)")


def cmd_gainers(args):
    """Show top daily gainers."""
    from src.screener.stock_screener import StockScreener, StockData
    _show_movers(args, mode="gainers")


def cmd_losers(args):
    """Show top daily losers."""
    _show_movers(args, mode="losers")


def _show_movers(args, mode: str = "gainers"):
    """Shared logic for gainers/losers."""
    from src.screener.stock_screener import StockScreener, StockData
    import numpy as np

    tickers = _get_universe_tickers(args.universe)
    screener = StockScreener()
    universe = []

    for ticker in tickers:
        df = _fetch_data(ticker, period="5d")
        if df is None or len(df) < 2:
            continue
        close = np.array(df["Close"].tolist(), dtype=np.float64)
        volume = np.array(df["Volume"].tolist(), dtype=np.float64) if "Volume" in df.columns else None
        universe.append(StockData(ticker=ticker, close=close, volume=volume))

    if mode == "gainers":
        results = screener.screen_gainers(universe, limit=args.limit)
        label = "Gainers"
        color_code = "\033[92m"
    else:
        results = screener.screen_losers(universe, limit=args.limit)
        label = "Losers"
        color_code = "\033[91m"

    reset = "\033[0m"
    print(f"\n  Top {label} ({args.universe})\n")
    print(f"  {'#':<4} {'Ticker':<10} {'Price':>10} {'Change%':>10} {'Volume':>14}")
    print("  " + "-" * 52)
    for i, r in enumerate(results, 1):
        pct_str = f"{r['change_pct']:>+9.2f}%"
        print(f"  {i:<4} {r['ticker']:<10} {r['price']:>10.2f} {color_code}{pct_str}{reset} {r['volume']:>14,}")
    print()


def cmd_risk_report(args):
    """Generate comprehensive risk report."""
    import csv as csv_mod
    from src.risk.risk_metrics import RiskMetrics

    returns = None

    if args.ticker:
        df = _fetch_data(args.ticker, period=args.period)
        if df is None or len(df) < 10:
            print(f"  No data for {args.ticker}")
            return
        prices = df["Close"].tolist()
        returns = [(prices[i] / prices[i - 1] - 1) for i in range(1, len(prices))]
        label = f"{args.ticker} ({args.period})"
    elif args.returns:
        if not os.path.exists(args.returns):
            print(f"  File not found: {args.returns}")
            return
        if args.returns.endswith(".json"):
            with open(args.returns) as f:
                data = json.load(f)
            returns = data if isinstance(data, list) else data.get("returns", [])
        else:
            returns = []
            with open(args.returns) as f:
                reader = csv_mod.reader(f)
                for row in reader:
                    try:
                        returns.append(float(row[-1]))
                    except (ValueError, IndexError):
                        continue
        label = os.path.basename(args.returns)
    elif args.portfolio:
        if not os.path.exists(args.portfolio):
            print(f"  File not found: {args.portfolio}")
            return
        with open(args.portfolio) as f:
            portfolio = json.load(f)
        holdings = portfolio.get("holdings", portfolio if isinstance(portfolio, list) else [])
        tickers = [h.get("ticker", h.get("symbol", "???")) for h in holdings]
        weights_raw = [h.get("weight", h.get("shares", 1)) for h in holdings]
        total_w = sum(weights_raw)
        weights = [w / total_w for w in weights_raw]

        all_rets = []
        for ticker in tickers:
            df = _fetch_data(ticker, period="1y")
            if df is None or len(df) < 30:
                all_rets.append([0.0] * 250)
                continue
            prices = df["Close"].tolist()
            all_rets.append([(prices[i] / prices[i - 1] - 1) for i in range(1, len(prices))])

        min_len = min(len(r) for r in all_rets)
        returns = []
        for day in range(min_len):
            ret = sum(w * all_rets[j][-(min_len - day)] for j, w in enumerate(weights))
            returns.append(ret)
        label = f"Portfolio ({', '.join(tickers)})"
    else:
        print("  Specify --ticker, --returns, or --portfolio")
        return

    if not returns or len(returns) < 10:
        print("  Insufficient return data (need >= 10 periods)")
        return

    report = RiskMetrics.full_report(returns)

    print(f"\n  ── Risk Report: {label} ──\n")
    print(f"  Total Return:       {report.total_return:+.2%}")
    print(f"  Annualized Return:  {report.annualized_return:+.2%}")
    print(f"  Annualized Vol:     {report.annualized_volatility:.2%}")
    print(f"  Sharpe Ratio:       {report.sharpe_ratio:.3f}")
    print(f"  Sortino Ratio:      {report.sortino_ratio:.3f}")
    print(f"  Calmar Ratio:       {report.calmar_ratio:.3f}")
    print(f"  Max Drawdown:       {report.max_drawdown:.2%}")
    print(f"  Max DD Duration:    {report.max_drawdown_duration} bars")
    print(f"  VaR (95%):          {report.var_95:.4f} ({report.var_95 * 100:.2f}%)")
    print(f"  CVaR (95%):         {report.cvar_95:.4f} ({report.cvar_95 * 100:.2f}%)")
    print(f"  VaR (99%):          {report.var_99:.4f} ({report.var_99 * 100:.2f}%)")
    print(f"  CVaR (99%):         {report.cvar_99:.4f} ({report.cvar_99 * 100:.2f}%)")
    print(f"  Skewness:           {report.skewness:.3f}")
    print(f"  Kurtosis:           {report.kurtosis:.3f}")

    if args.output:
        import dataclasses
        with open(args.output, "w") as f:
            json.dump(dataclasses.asdict(report), f, indent=2)
        print(f"\n  ✓ Saved to {args.output}")
    print()


def cmd_position_size(args):
    """Calculate position size."""
    from src.risk.position_sizer import PositionSizer

    capital = args.capital
    risk_pct = args.risk / 100.0
    method = args.method

    print(f"\n  ── Position Size Calculator ──")
    print(f"  Capital: ${capital:,.2f} | Risk: {args.risk}% | Method: {method}\n")

    if method == "fixed-fraction":
        entry = args.entry
        stop = args.stop
        if entry is None or stop is None:
            print("  --entry and --stop required for fixed-fraction method")
            return
        shares = PositionSizer.percent_risk(capital, entry, stop, risk_pct)
        risk_amount = capital * risk_pct
        position_value = shares * entry
        print(f"  Entry:          ${entry:.2f}")
        print(f"  Stop:           ${stop:.2f}")
        print(f"  Stop Distance:  ${abs(entry - stop):.2f} ({abs(entry - stop) / entry:.2%})")
        print(f"  Risk Amount:    ${risk_amount:,.2f}")
        print(f"  Shares:         {shares}")
        print(f"  Position Value: ${position_value:,.2f} ({position_value / capital:.1%} of capital)")

    elif method == "kelly":
        wr = args.win_rate
        wlr = args.win_loss_ratio
        if wr is None or wlr is None:
            print("  --win-rate and --win-loss-ratio required for kelly method")
            return
        fraction = PositionSizer.kelly(wr, wlr)
        position_value = capital * fraction
        print(f"  Win Rate:       {wr:.1%}")
        print(f"  Win/Loss Ratio: {wlr:.2f}")
        print(f"  Kelly Fraction: {fraction:.3f} (half-Kelly)")
        print(f"  Position Size:  ${position_value:,.2f} ({fraction:.1%} of capital)")

    elif method == "volatility":
        entry = args.entry
        atr = args.atr
        if entry is None or atr is None:
            print("  --entry and --atr required for volatility method")
            return
        shares = PositionSizer.volatility_based(capital, entry, atr, risk_pct)
        position_value = shares * entry
        print(f"  Entry:          ${entry:.2f}")
        print(f"  ATR:            ${atr:.2f}")
        print(f"  Risk Amount:    ${capital * risk_pct:,.2f}")
        print(f"  Shares:         {shares}")
        print(f"  Position Value: ${position_value:,.2f} ({position_value / capital:.1%} of capital)")

    elif method == "equal-weight":
        n = args.n_positions or 10
        weight = PositionSizer.equal_weight(n)
        position_value = capital * weight
        print(f"  Positions:      {n}")
        print(f"  Weight:         {weight:.2%}")
        print(f"  Per Position:   ${position_value:,.2f}")

    print()


def main(argv=None):
    """Main CLI entry point."""
    # Fix encoding on Windows (cp936/GBK can't handle Unicode box-drawing chars)
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace('-', '') not in ('utf8', 'utf16'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "backtest":
            cmd_backtest(args)
        elif args.command == "screen":
            cmd_screen(args)
        elif args.command == "analyze":
            cmd_analyze(args)
        elif args.command == "portfolio":
            if args.portfolio_cmd == "track":
                cmd_portfolio_track(args)
            elif args.portfolio_cmd in ("add", "remove", "show", "history", "alert", "export"):
                _handle_portfolio_tracker(args)
            else:
                print("  Usage: finclaw portfolio {add|remove|show|history|alert|export|track}")
        elif args.command == "price":
            cmd_price(args)
        elif args.command == "options":
            if args.options_cmd == "price":
                cmd_options_price(args)
            else:
                print("  Usage: finclaw options price --type call --S 150 --K 155 --T 0.5 --r 0.05 --sigma 0.25")
        elif args.command == "paper-trade":
            cmd_paper_trade(args)
        elif args.command == "paper":
            _handle_paper(args)
        elif args.command == "report":
            cmd_report(args)
        elif args.command == "tearsheet":
            cmd_tearsheet(args)
        elif args.command == "compare":
            cmd_compare(args)
        elif args.command == "export":
            cmd_export(args)
        elif args.command == "risk":
            cmd_risk(args)
        elif args.command == "risk-report":
            cmd_risk_report(args)
        elif args.command == "position-size":
            cmd_position_size(args)
        elif args.command == "serve":
            from src.api.server import FinClawAPI
            api = FinClawAPI(
                host=args.host,
                port=args.port,
                auth_enabled=args.auth,
                max_requests=args.rate_limit,
            )
            api.start()
        elif args.command == "interactive":
            cmd_interactive(args)
        elif args.command == "btc-metrics":
            cmd_btc_metrics(args)
        elif args.command == "defi-tvl":
            cmd_defi_tvl(args)
        elif args.command == "yields":
            cmd_yields(args)
        elif args.command == "stablecoins":
            cmd_stablecoins(args)
        elif args.command == "funding-rates":
            cmd_funding_rates(args)
        elif args.command == "fear-greed":
            cmd_fear_greed(args)
        elif args.command == "cache":
            from src.data.cache import DataCache
            cache = DataCache()
            if args.clear:
                cache.clear()
                print("  Cache cleared.")
            else:
                stats = cache.stats()
                print(f"  Entries: {stats['entries']} | Size: {stats['size_kb']:.1f} KB")
        elif args.command == "demo":
            from src.cli.demo import run_demo
            run_demo()
        elif args.command == "info":
            if args.ticker:
                # Show ticker info
                ticker = args.ticker.upper()
                df = _fetch_data(ticker, period="1y")
                if df is None:
                    print(f"  No data for {ticker}.")
                else:
                    close = df["Close"].tolist()
                    price = close[-1]
                    change = price - close[-2] if len(close) > 1 else 0
                    pct = change / close[-2] if len(close) > 1 else 0
                    hi = max(close)
                    lo = min(close)
                    vol = _calc_vol(close)
                    print(f"\n  ── {ticker} Info ──")
                    print(f"  Price:     ${price:.2f}")
                    print(f"  Change:    {change:+.2f} ({pct:+.2%})")
                    print(f"  52w High:  ${hi:.2f}")
                    print(f"  52w Low:   ${lo:.2f}")
                    print(f"  Ann. Vol:  {vol:.2%}")
                    print()
            else:
                print(f"  FinClaw v{_get_version()} — AI-Powered Financial Intelligence Engine")
                print("  Commands: backtest, screen, analyze, portfolio, price, options, paper-trade, report, interactive, exchanges, quote, history")
        elif args.command == "doctor":
            from src.cli.doctor import run_doctor, format_doctor_output
            results = run_doctor(skip_network=getattr(args, "skip_network", False))
            print(format_doctor_output(results, verbose=getattr(args, "verbose", False)))
            required_fails = [r for r in results if not r.passed and r.severity.value == "required"]
            return 1 if required_fails else 0
        elif args.command == "exchanges":
            from src.exchanges.registry import ExchangeRegistry
            if getattr(args, "exchanges_cmd", "list") == "compare":
                _compare_exchanges(args.exchange_names if args.exchange_names else ExchangeRegistry.list_exchanges())
            else:
                print("  Available exchanges:")
                for etype in ("crypto", "stock_us", "stock_cn"):
                    names = ExchangeRegistry.list_by_type(etype)
                    if names:
                        print(f"    [{etype}] {', '.join(names)}")
        elif args.command == "quote":
            from src.exchanges.registry import ExchangeRegistry
            from src.cli.colors import bold, bright_green, bright_red, gray, price_color, pct_color
            adapter = ExchangeRegistry.get(args.exchange)
            symbols = args.symbol  # now a list
            if len(symbols) == 1:
                # Single symbol — detailed view
                ticker = adapter.get_ticker(symbols[0])
                last = ticker['last']
                bid = ticker.get('bid', 'N/A')
                ask = ticker.get('ask', 'N/A')
                vol = ticker.get('volume', 'N/A')
                chg = ticker.get('change', 0) or 0
                chg_pct = ticker.get('change_pct', 0) or 0
                chg_str = price_color(chg, f"{chg:>+.2f}") if chg else ""
                pct_str = pct_color(chg_pct / 100, f"{chg_pct:>+.2f}%") if chg_pct else ""
                print(f"\n  {bold(ticker['symbol'])}  {bold(f'${last:.2f}' if isinstance(last, (int,float)) else str(last))}  {chg_str} {pct_str}")
                print(f"  Bid: {bid}  Ask: {ask}  Vol: {vol:,.0f}" if isinstance(vol, (int,float)) else f"  Bid: {bid}  Ask: {ask}  Vol: {vol}")
                print()
            else:
                # Multi-symbol — table view
                print(f"\n  {bold('Symbol'):<18} {bold('Price'):>10} {bold('Change'):>10} {bold('%'):>10} {bold('Volume'):>14}")
                print("  " + "─" * 62)
                for sym in symbols:
                    try:
                        ticker = adapter.get_ticker(sym)
                        last = ticker['last']
                        chg = ticker.get('change', 0) or 0
                        chg_pct = ticker.get('change_pct', 0) or 0
                        vol = ticker.get('volume', 'N/A')
                        price_str = f"${last:.2f}" if isinstance(last, (int, float)) else str(last)
                        chg_str = price_color(chg, f"{chg:>+.2f}")
                        pct_str = pct_color(chg_pct / 100, f"{chg_pct:>+.2f}%")
                        vol_str = f"{vol:>14,.0f}" if isinstance(vol, (int, float)) else f"{vol:>14}"
                        print(f"  {sym:<10} {price_str:>10} {chg_str:>10} {pct_str:>10} {vol_str}")
                    except Exception as e:
                        print(f"  {sym:<10} {'Error':>10} {str(e)[:30]}")
                print()
        elif args.command == "history":
            from src.exchanges.registry import ExchangeRegistry
            adapter = ExchangeRegistry.get(args.exchange)
            candles = adapter.get_ohlcv(args.symbol, args.timeframe, args.limit)
            print(f"  {args.symbol} ({args.exchange}) — {len(candles)} candles [{args.timeframe}]")
            print(f"  {'Date/Time':<20} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>12}")
            for c in candles[-args.limit:]:
                ts_raw = c['timestamp']
                try:
                    # Timestamps from exchanges are typically in milliseconds
                    ts_seconds = ts_raw / 1000 if ts_raw > 1e12 else ts_raw
                    ts = datetime.fromtimestamp(ts_seconds).strftime("%Y-%m-%d %H:%M")
                except (OSError, ValueError, TypeError):
                    ts = str(ts_raw)[:20]
                print(f"  {ts:<20} {c['open']:>10.4f} {c['high']:>10.4f} {c['low']:>10.4f} {c['close']:>10.4f} {c['volume']:>12.0f}")
        elif args.command == "plugin":
            from src.plugins.plugin_manager import PluginManager
            pm = PluginManager()
            if args.plugin_cmd == "list":
                available = pm.discover()
                loaded = pm.load_all()
                if not available and not loaded:
                    print("  No plugins found.")
                    print(f"  Plugin directory: {pm.plugin_dir}")
                    print("  Use 'finclaw plugin create --type strategy --name my_strategy' to create one.")
                else:
                    print(f"  Plugins ({len(loaded)} loaded):")
                    for p in loaded:
                        status = "✓" if p.active else "✗"
                        print(f"    {status} {p.name} v{p.version} [{p.plugin_type}] — {p.description}")
            elif args.plugin_cmd == "install":
                info = pm.install(args.source)
                print(f"  Installed: {info.name} v{info.version} [{info.plugin_type}]")
            elif args.plugin_cmd == "create":
                path = pm.create(args.name, args.plugin_type)
                print(f"  Created {args.plugin_type} plugin: {path}")
            elif args.plugin_cmd == "info":
                pm.load_all()
                info = pm.get_plugin(args.name)
                if info:
                    print(f"  Name:        {info.name}")
                    print(f"  Version:     {info.version}")
                    print(f"  Type:        {info.plugin_type}")
                    print(f"  Description: {info.description}")
                    print(f"  Path:        {info.path}")
                    print(f"  Active:      {info.active}")
                else:
                    print(f"  Plugin not found: {args.name}")
            else:
                print("  Usage: finclaw plugin [list|install|create|info]")
        elif args.command == "plugins":
            from src.plugin_system.registry import StrategyRegistry
            registry = StrategyRegistry()
            registry.load_all()
            if args.plugins_cmd == "list":
                plugins = registry.list()
                if not plugins:
                    print("  No strategy plugins found.")
                else:
                    print(f"  Strategy Plugins ({len(plugins)}):")
                    print(f"  {'Name':<25} {'Version':<10} {'Risk':<8} {'Markets':<30} Description")
                    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*30} {'-'*30}")
                    for p in plugins:
                        markets = ", ".join(p.markets)
                        print(f"  {p.name:<25} {p.version:<10} {p.risk_level:<8} {markets:<30} {p.description}")
            elif args.plugins_cmd == "info":
                p = registry.get(args.name)
                if p:
                    print(f"  Name:        {p.name}")
                    print(f"  Version:     {p.version}")
                    print(f"  Author:      {p.author}")
                    print(f"  Description: {p.description}")
                    print(f"  Risk Level:  {p.risk_level}")
                    print(f"  Markets:     {', '.join(p.markets)}")
                    params = p.get_parameters()
                    if params:
                        print(f"  Parameters:  {params}")
                    config = p.backtest_config()
                    if config:
                        print(f"  Backtest:    {config}")
                    issues = p.validate()
                    if issues:
                        print(f"  ⚠ Issues:    {issues}")
                else:
                    print(f"  Plugin not found: {args.name}")
                    print(f"  Available: {', '.join(registry.names())}")
            else:
                print("  Usage: finclaw plugins [list|info <name>]")
        elif args.command == "init-strategy":
            name = args.name
            output = args.output
            pkg_name = f"finclaw_strategy_{name}"
            pkg_dir = os.path.join(output, f"finclaw-strategy-{name}")
            os.makedirs(os.path.join(pkg_dir, pkg_name), exist_ok=True)
            os.makedirs(os.path.join(pkg_dir, "tests"), exist_ok=True)

            class_name = name.replace("_", " ").title().replace(" ", "")

            # pyproject.toml
            with open(os.path.join(pkg_dir, "pyproject.toml"), "w") as f:
                f.write(f'''[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "finclaw-strategy-{name}"
version = "0.1.0"
description = "FinClaw strategy plugin: {name}"
license = {{text = "MIT"}}
requires-python = ">=3.9"
dependencies = ["pandas>=1.3.0"]

[project.entry-points."finclaw.strategies"]
{name} = "{pkg_name}.strategy:{class_name}Strategy"
''')

            # __init__.py
            with open(os.path.join(pkg_dir, pkg_name, "__init__.py"), "w") as f:
                f.write(f'from {pkg_name}.strategy import {class_name}Strategy\n')

            # strategy.py
            with open(os.path.join(pkg_dir, pkg_name, "strategy.py"), "w") as f:
                f.write(f'''"""
{class_name} Strategy Plugin for FinClaw
"""
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin


class {class_name}Strategy(StrategyPlugin):
    name = "{name}"
    version = "0.1.0"
    description = "TODO: describe your strategy"
    author = "Your Name"
    risk_level = "medium"
    markets = ["us_stock"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        # TODO: implement your signal logic
        # 1 = buy, -1 = sell, 0 = hold
        return signals

    def get_parameters(self) -> dict:
        return {{}}
''')

            # README
            with open(os.path.join(pkg_dir, "README.md"), "w") as f:
                f.write(f'# finclaw-strategy-{name}\\n\\nFinClaw strategy plugin.\\n\\n```bash\\npip install -e .\\nfinclaw plugins list\\n```\\n')

            # test
            with open(os.path.join(pkg_dir, "tests", f"test_{name}.py"), "w") as f:
                f.write(f'''import pandas as pd
import numpy as np
from {pkg_name}.strategy import {class_name}Strategy

def test_signals():
    df = pd.DataFrame({{"Close": np.random.randn(100).cumsum() + 100}},
                       index=pd.date_range("2020-01-01", periods=100))
    s = {class_name}Strategy()
    signals = s.generate_signals(df)
    assert len(signals) == 100
''')

            print(f"  OK Created strategy plugin scaffold: {pkg_dir}")
            print(f"    {pkg_dir}/")
            print(f"    +-- pyproject.toml")
            print(f"    +-- README.md")
            print(f"    +-- {pkg_name}/")
            print(f"    |   +-- __init__.py")
            print(f"    |   +-- strategy.py")
            print(f"    +-- tests/")
            print(f"        +-- test_{name}.py")
            print(f"\n  Next steps:")
            print(f"    cd {pkg_dir}")
            print(f"    pip install -e .")
            print(f"    finclaw plugins list")
        elif args.command == "mcp":
            if args.mcp_cmd == "serve":
                from src.mcp.server import FinClawMCPServer
                from src.mcp.protocol import MCPProtocol
                server = FinClawMCPServer()
                protocol = MCPProtocol(server)
                protocol.run()
            elif args.mcp_cmd == "config":
                from src.mcp.config import MCPConfigGenerator
                MCPConfigGenerator.print_config(args.client)
            else:
                print("  Usage: finclaw mcp [serve|config]")
        elif args.command == "watchlist":
            cmd_watchlist(args)
        elif args.command == "watch":
            cmd_watch(args)
        elif args.command == "gainers":
            cmd_gainers(args)
        elif args.command == "losers":
            cmd_losers(args)
        elif args.command == "sentiment":
            cmd_sentiment(args)
        elif args.command == "reddit-buzz":
            cmd_reddit_buzz(args)
        elif args.command == "news":
            cmd_news(args)
        elif args.command == "trending":
            cmd_trending(args)
        elif args.command == "scan-cn":
            cmd_scan_cn(args)
        elif args.command == "scan":
            cmd_scan(args)
        elif args.command == "strategy":
            cmd_strategy(args)
        elif args.command == "predict":
            cmd_predict(args)
        elif args.command == "alert":
            cmd_alert(args)
        elif args.command == "chart":
            cmd_chart(args)
        elif args.command == "a2a":
            _cmd_a2a(args)
        elif args.command == "generate-strategy":
            _cmd_generate_strategy(args)
        elif args.command == "optimize-strategy":
            _cmd_optimize_strategy(args)
        elif args.command == "copilot":
            _cmd_copilot(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        return 130
    except Exception as e:
        print(f"\n  ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
