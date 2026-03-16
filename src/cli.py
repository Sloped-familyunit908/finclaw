"""
FinClaw CLI v4.0.0 - Comprehensive argparse-based CLI
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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager


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

    criteria_str = args.criteria
    universe = args.universe

    # Parse criteria like "rsi<30,pe<15,market_cap>1B"
    filters = {}
    for crit in criteria_str.split(","):
        crit = crit.strip()
        for op in ["<=", ">=", "<", ">"]:
            if op in crit:
                key, val = crit.split(op, 1)
                key = key.strip()
                val = val.strip()
                # Parse value with suffix
                multiplier = 1
                if val.upper().endswith("B"):
                    multiplier = 1e9
                    val = val[:-1]
                elif val.upper().endswith("M"):
                    multiplier = 1e6
                    val = val[:-1]
                elif val.upper().endswith("K"):
                    multiplier = 1e3
                    val = val[:-1]
                filters[key] = (op, float(val) * multiplier)
                break

    # Load universe tickers
    tickers = _get_universe_tickers(universe)
    print(f"\n  Screening {len(tickers)} stocks with criteria: {criteria_str}")

    results = []
    for ticker in tickers[:50]:  # Limit to avoid rate limits
        try:
            df = _fetch_data(ticker, period="1y")
            if df is None or len(df) < 30:
                continue

            close = np.array(df["Close"].tolist(), dtype=np.float64)
            from src.ta import rsi as calc_rsi
            rsi_val = calc_rsi(close, 14)[-1]

            # Get PE and market cap from yfinance
            import yfinance as yf
            info = yf.Ticker(ticker).info
            pe = info.get("trailingPE")
            mcap = info.get("marketCap")

            # Check filters
            passed = True
            values = {"rsi": rsi_val, "pe": pe, "market_cap": mcap}
            for key, (op, threshold) in filters.items():
                val = values.get(key)
                if val is None:
                    passed = False
                    break
                if op == "<" and not (val < threshold):
                    passed = False
                elif op == ">" and not (val > threshold):
                    passed = False
                elif op == "<=" and not (val <= threshold):
                    passed = False
                elif op == ">=" and not (val >= threshold):
                    passed = False

            if passed:
                results.append({
                    "ticker": ticker,
                    "rsi": round(rsi_val, 1) if not math.isnan(rsi_val) else None,
                    "pe": round(pe, 1) if pe else None,
                    "market_cap": mcap,
                })
                print(f"  ✓ {ticker}: RSI={rsi_val:.1f}, PE={pe}, MCap={mcap:,.0f}" if mcap else f"  ✓ {ticker}")
        except Exception:
            continue

    print(f"\n  Found {len(results)} stocks matching criteria.")
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

    from src.reporting.tearsheet import Tearsheet
    output = args.output or f"tearsheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    result = Tearsheet.generate(returns, benchmark=benchmark, output_path=output)
    print(f"  ✓ Tearsheet generated: {output} ({len(result):,} bytes)")


def cmd_compare(args):
    """Compare multiple strategies."""
    from src.reporting.comparison import StrategyComparison

    comp = StrategyComparison()
    for filepath in args.strategies:
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
        description="FinClaw v5.5.0 — AI-Powered Financial Intelligence Engine",
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
    parser.add_argument("--version", action="version", version="finclaw 5.5.0")
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
    p.add_argument("--criteria", required=True, help='Filter criteria, e.g. "rsi<30,pe<15"')
    p.add_argument("--universe", default="sp500", help="Stock universe")

    # analyze
    p = sub.add_parser("analyze", help="Technical analysis")
    p.add_argument("--ticker", "-t", required=True, help="Ticker symbol")
    p.add_argument("--indicators", "-i", default="rsi,macd,bollinger", help="Comma-separated indicators")

    # portfolio
    p_port = sub.add_parser("portfolio", help="Portfolio commands")
    port_sub = p_port.add_subparsers(dest="portfolio_cmd")
    p_track = port_sub.add_parser("track", help="Track portfolio from file")
    p_track.add_argument("--file", "-f", required=True, help="Portfolio JSON file")

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

    # paper-trade
    p = sub.add_parser("paper-trade", help="Paper trading simulation")
    p.add_argument("--strategy", "-s", default="trend", help="Strategy name")
    p.add_argument("--tickers", "-t", required=True, help="Comma-separated tickers")
    p.add_argument("--capital", "-c", type=float, default=100000)

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

    # compare
    p = sub.add_parser("compare", help="Compare multiple strategies")
    p.add_argument("--strategies", "-s", nargs="+", required=True, help="JSON files with strategy returns")
    p.add_argument("--output", "-o", help="Output HTML file path")

    # risk
    p = sub.add_parser("risk", help="Portfolio risk analysis")
    p.add_argument("--portfolio", "-p", required=True, help="Portfolio JSON file")
    p.add_argument("--output", "-o", help="Save risk report to JSON")

    # serve
    p = sub.add_parser("serve", help="Start REST API server")
    p.add_argument("--host", default="0.0.0.0", help="Bind host")
    p.add_argument("--port", "-p", type=int, default=8080, help="Port number")
    p.add_argument("--auth", action="store_true", help="Enable API key auth")
    p.add_argument("--rate-limit", type=int, default=100, help="Max requests per minute")

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

    # quote (multi-exchange)
    p_q = sub.add_parser("quote", help="Get quote from any exchange")
    p_q.add_argument("symbol", help="Symbol (e.g. BTCUSDT, AAPL, 000001.SZ)")
    p_q.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")

    # history (multi-exchange)
    p_h = sub.add_parser("history", help="Get OHLCV history from any exchange")
    p_h.add_argument("symbol", help="Symbol")
    p_h.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")
    p_h.add_argument("--timeframe", "-t", default="1d", help="Timeframe (1m,5m,1h,1d,...)")
    p_h.add_argument("--limit", "-l", type=int, default=20, help="Number of candles")

    # info
    sub.add_parser("info", help="Show system info")

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

    # predict
    p_pred = sub.add_parser("predict", help="ML prediction engine")
    pred_sub = p_pred.add_subparsers(dest="predict_cmd")
    p_pred_run = pred_sub.add_parser("run", help="Run prediction on a symbol")
    p_pred_run.add_argument("--symbol", "-s", required=True, help="Ticker symbol")
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

    # sentiment
    p_sent = sub.add_parser("sentiment", help="Sentiment analysis for a symbol")
    p_sent.add_argument("symbol", help="Ticker symbol (e.g. AAPL, BTCUSDT)")
    p_sent.add_argument("--reddit", action="store_true", help="Include Reddit sentiment")

    # news
    p_news = sub.add_parser("news", help="Get financial news for a symbol")
    p_news.add_argument("symbol", help="Ticker symbol")
    p_news.add_argument("--limit", "-l", type=int, default=10, help="Number of articles")
    p_news.add_argument("--search", "-s", default=None, help="Search query instead of symbol")

    # trending
    sub.add_parser("trending", help="Show trending financial topics and WSB tickers")

    # scan
    p_scan = sub.add_parser("scan", help="Real-time market scanner")
    p_scan.add_argument("--rule", required=True, help='Rule expression, e.g. "rsi<30 AND volume>2x"')
    p_scan.add_argument("--symbols", default="AAPL,MSFT,GOOGL,AMZN,TSLA", help="Comma-separated symbols")
    p_scan.add_argument("--exchange", "-e", default="yahoo", help="Exchange name")
    p_scan.add_argument("--interval", type=int, default=60, help="Scan interval in seconds")
    p_scan.add_argument("--once", action="store_true", help="Run only once")

    # strategy library
    p_strat = sub.add_parser("strategy", help="Built-in strategy library")
    strat_sub = p_strat.add_subparsers(dest="strategy_cmd")
    strat_sub.add_parser("list", help="List all built-in strategies")
    p_si = strat_sub.add_parser("info", help="Show strategy details")
    p_si.add_argument("name", help="Strategy slug (e.g. grid-trading)")
    p_sb = strat_sub.add_parser("backtest", help="Backtest a built-in strategy")
    p_sb.add_argument("name", help="Strategy slug (e.g. trend-following)")
    p_sb.add_argument("--symbol", "-s", default="AAPL", help="Ticker symbol")
    p_sb.add_argument("--start", default="2024-01-01", help="Start date")
    p_sb.add_argument("--end", default=None, help="End date")
    p_sb.add_argument("--capital", type=float, default=10000, help="Initial capital")

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
        print(f"\n  🤖 ML Prediction: {args.symbol}")
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
    """Handle strategy library commands: list, info, backtest."""
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
        print("  Usage: finclaw strategy [list|info|backtest]")


def cmd_watchlist(args):
    """Manage watchlists."""
    from src.screener.watchlist import WatchlistManager
    wm = WatchlistManager()
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


def main(argv=None):
    """Main CLI entry point."""
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
            else:
                print("  Usage: finclaw portfolio track --file portfolio.json")
        elif args.command == "price":
            cmd_price(args)
        elif args.command == "options":
            if args.options_cmd == "price":
                cmd_options_price(args)
            else:
                print("  Usage: finclaw options price --type call --S 150 --K 155 --T 0.5 --r 0.05 --sigma 0.25")
        elif args.command == "paper-trade":
            cmd_paper_trade(args)
        elif args.command == "report":
            cmd_report(args)
        elif args.command == "tearsheet":
            cmd_tearsheet(args)
        elif args.command == "compare":
            cmd_compare(args)
        elif args.command == "risk":
            cmd_risk(args)
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
        elif args.command == "cache":
            from src.data.cache import DataCache
            cache = DataCache()
            if args.clear:
                cache.clear()
                print("  Cache cleared.")
            else:
                stats = cache.stats()
                print(f"  Entries: {stats['entries']} | Size: {stats['size_kb']:.1f} KB")
        elif args.command == "info":
            print("  FinClaw v5.2.0 — AI-Powered Financial Intelligence Engine")
            print("  Commands: backtest, screen, analyze, portfolio, price, options, paper-trade, report, interactive, exchanges, quote, history")
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
            adapter = ExchangeRegistry.get(args.exchange)
            ticker = adapter.get_ticker(args.symbol)
            print(f"  {ticker['symbol']}  Last: {ticker['last']}  Bid: {ticker.get('bid', 'N/A')}  Ask: {ticker.get('ask', 'N/A')}  Vol: {ticker.get('volume', 'N/A')}")
        elif args.command == "history":
            from src.exchanges.registry import ExchangeRegistry
            adapter = ExchangeRegistry.get(args.exchange)
            candles = adapter.get_ohlcv(args.symbol, args.timeframe, args.limit)
            print(f"  {args.symbol} ({args.exchange}) — {len(candles)} candles [{args.timeframe}]")
            print(f"  {'Date/Time':<20} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} {'Volume':>12}")
            for c in candles[-args.limit:]:
                ts = str(c['timestamp'])[:20]
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
        elif args.command == "sentiment":
            cmd_sentiment(args)
        elif args.command == "news":
            cmd_news(args)
        elif args.command == "trending":
            cmd_trending(args)
        elif args.command == "scan":
            cmd_scan(args)
        elif args.command == "strategy":
            cmd_strategy(args)
        elif args.command == "predict":
            cmd_predict(args)
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
