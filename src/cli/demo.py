"""
FinClaw Demo Mode — showcase all features with pre-baked data.
No API keys, no internet required.
"""

import math
import random
from datetime import datetime, timedelta

from src.cli.colors import (
    banner, header, bold, dim, cyan, green, red, yellow, gray,
    bright_green, bright_red, bright_cyan, price_color, pct_color, signal_color,
)


def _fake_prices(start=150.0, days=252, volatility=0.02, trend=0.0003):
    """Generate realistic-looking price series."""
    prices = [start]
    for _ in range(days - 1):
        ret = trend + volatility * random.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def _sparkline(values, width=20):
    """Mini sparkline chart."""
    blocks = " ▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    step = len(values) / width
    result = ""
    for i in range(width):
        idx = min(int(i * step), len(values) - 1)
        level = int((values[idx] - mn) / rng * 8)
        result += blocks[level]
    return result


def run_demo():
    """Run the full demo showcase."""
    print(banner())
    print(bold("  🎬 FinClaw Demo — All features, zero config\n"))
    print(dim("  Using pre-generated data. No API keys needed.\n"))

    # ── Section 1: Live Quotes ──
    print(header("  ━━━ 📊 Real-Time Quotes ━━━\n"))
    quotes = [
        ("AAPL", 189.84, +2.31, +1.23),
        ("NVDA", 875.28, +15.67, +1.82),
        ("TSLA", 175.21, -3.45, -1.93),
        ("MSFT", 415.50, +1.02, +0.25),
        ("GOOGL", 153.78, -0.89, -0.58),
    ]
    print(f"  {'Symbol':<8} {'Price':>10} {'Change':>10} {'   %':>8}  {'Trend':>20}")
    print(gray(f"  {'─' * 60}"))
    for sym, price, chg, pct in quotes:
        spark_data = _fake_prices(price - abs(chg) * 5, days=30, volatility=0.015)
        spark = _sparkline(spark_data)
        chg_str = price_color(chg, f"{chg:>+8.2f}")
        pct_str = pct_color(pct / 100, f"{pct:>+6.2f}%")
        print(f"  {bold(sym):<16} {price:>10.2f} {chg_str} {pct_str}  {cyan(spark)}")
    print()

    # ── Section 2: Technical Analysis ──
    print(header("  ━━━ 🔬 Technical Analysis: NVDA ━━━\n"))
    print(f"  Price: {bold('$875.28')}  |  52w High: {green('$950.02')}  |  52w Low: {red('$410.15')}")
    print()
    indicators = [
        ("RSI(14)", "62.4", "NEUTRAL", "momentum balanced"),
        ("MACD", "+4.82", "BULLISH", "histogram expanding"),
        ("SMA(50)", "$842.10", "ABOVE", "price above trend"),
        ("SMA(200)", "$695.30", "ABOVE", "strong uptrend"),
        ("Bollinger", "72%B", "NEUTRAL", "upper half of band"),
    ]
    for name, val, sig, note in indicators:
        sig_str = signal_color(sig)
        print(f"  {name:<14} {bold(val):>16}  {sig_str:<20}  {dim(note)}")
    print()

    # ── Section 3: Backtest ──
    print(header("  ━━━ 🚀 Backtest: Momentum Strategy on AAPL ━━━\n"))
    random.seed(42)
    prices = _fake_prices(130, 504, 0.018, 0.0005)
    bh_ret = prices[-1] / prices[0] - 1
    strat_ret = bh_ret + 0.08
    ann_ret = (1 + strat_ret) ** (1 / 2) - 1

    print(f"  Period:    2y (504 trading days)")
    print(f"  Capital:   $100,000")
    print()
    print(f"  Strategy:  {pct_color(strat_ret, f'{strat_ret:+.1%}')}  ({pct_color(ann_ret, f'{ann_ret:+.1%}')}/yr)")
    print(f"  Buy&Hold:  {pct_color(bh_ret, f'{bh_ret:+.1%}')}")
    print(f"  Alpha:     {bright_green(f'+{strat_ret - bh_ret:.1%}')}")
    print(f"  MaxDD:     {bright_red('-8.3%')}")
    print(f"  Sharpe:    {bold('1.85')}")
    print(f"  Trades:    47  |  Win Rate: {bold('63%')}")
    print(f"  P&L:       {bright_green(f'+${100000 * strat_ret:,.0f}')}")
    print()

    # Equity curve sparkline
    equity = [100000]
    for i in range(1, len(prices)):
        equity.append(equity[-1] * (1 + (prices[i] / prices[i - 1] - 1) * 1.2))
    print(f"  Equity:  {cyan(_sparkline(equity, 40))}")
    print()

    # ━━━ 🧬 Strategy Evolution Engine ━━━
    print(header("  ━━━ 🧬 Strategy Evolution Engine ━━━\n"))
    print("  FinClaw's core: genetic algorithms evolve strategies autonomously.")
    print("  Here's what 100 generations of evolution looks like:\n")

    # Pre-generated evolution progress (based on real Gen 89 best results)
    evo_data = [
        (1,    12.3,   45.2,  1.2,  "▁░░░░░░░░░"),
        (10,   34.5,  123.7,  2.1,  "██░░░░░░░░"),
        (25,   89.2,  456.3,  3.4,  "████░░░░░░"),
        (50,  234.7, 1205.8,  4.8,  "██████░░░░"),
        (75,  567.3, 2890.4,  5.6,  "████████░░"),
        (89, 2756.4, 4487.8,  6.6,  "██████████ 🏆"),
    ]

    print(f"  {'Gen':>5}  {'Return':>10}  {'Fitness':>10}  {'Sharpe':>7}  Progress")
    print(f"  {'─'*5}  {'─'*10}  {'─'*10}  {'─'*7}  {'─'*15}")
    for gen, ret, fit, sharpe, bar in evo_data:
        print(f"  {gen:>5}  {ret:>9.1f}%  {fit:>10.1f}  {sharpe:>7.1f}  {bar}")

    print(f"\n  DNA evolved across 484 factor dimensions:")
    print(f"  Top factors: RSI ×0.34, Momentum ×0.25, MACD ×0.18, Volume ×0.12")
    print(f"  Walk-forward validated: ✅  Monte Carlo robust: ✅")
    print()
    print(f"  Run your own evolution:")
    print(f"    {cyan('finclaw evolve --market crypto --generations 50')}")
    print(f"    {cyan('finclaw evolve --market a-share --generations 100')}")
    print()

    # ── Section 4: Paper Trading ──
    print(header("  ━━━ 📋 Paper Trading Portfolio ━━━\n"))
    positions = [
        ("AAPL", 50, 178.50, 189.84, +5650.0),
        ("NVDA", 20, 810.00, 875.28, +1305.6),
        ("MSFT", 30, 420.00, 415.50, -135.0),
    ]
    print(f"  {'Symbol':<8} {'Shares':>8} {'Avg Cost':>10} {'Price':>10} {'P&L':>12}")
    print(gray(f"  {'─' * 52}"))
    total_pnl = 0
    for sym, qty, cost, price, pnl in positions:
        total_pnl += pnl
        pnl_str = price_color(pnl, f"${pnl:>+10,.2f}")
        print(f"  {bold(sym):<16} {qty:>8} {cost:>10.2f} {price:>10.2f} {pnl_str}")
    print(gray(f"  {'─' * 52}"))
    print(f"  {'TOTAL':<16} {'':>8} {'':>10} {'':>10} {price_color(total_pnl, f'${total_pnl:>+10,.2f}')}")
    print()

    # ── Section 5: Risk Analysis ──
    print(header("  ━━━ 🛡️ Risk Analysis ━━━\n"))
    print(f"  Sharpe Ratio:      {bold('1.85')}")
    print(f"  Max Drawdown:      {bright_red('-8.3%')}")
    print(f"  VaR (95%):         {yellow('-2.1%')}")
    print(f"  Volatility (ann):  {bold('18.4%')}")
    print(f"  Beta:              {bold('0.92')}")
    print(f"  Diversification:   {green('Good')} (HHI: 0.18)")
    print()

    # ── Section 6: AI Features ──
    print(header("  ━━━ 🤖 AI Features ━━━\n"))
    print(f"  {bold('Strategy Generator')}  — Natural language → trading code")
    print(dim('    "buy when RSI < 30 and MACD crosses up, 5% stop loss"'))
    print()
    print(f"  {bold('Copilot')}             — Interactive AI financial assistant")
    print(dim('    "分析一下特斯拉最近走势" → full technical breakdown'))
    print()
    print(f"  {bold('MCP Server')}          — Expose FinClaw as tools for AI agents")
    print(dim('    Works with Claude, Cursor, VS Code, OpenClaw'))
    print()

    # ── Footer ──
    print(gray("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"))
    print()
    print(f"  {bold('Try it yourself:')}")
    print(f"    {cyan('finclaw quote AAPL')}            — Live stock quote")
    print(f"    {cyan('finclaw analyze TSLA')}          — Technical analysis")
    print(f"    {cyan('finclaw backtest -t AAPL')}      — Run a backtest")
    print(f"    {cyan('finclaw copilot')}               — AI financial chat")
    print(f"    {cyan('finclaw generate-strategy')}     — AI strategy builder")
    print()
    print(dim("  📖 Docs: https://github.com/NeuZhou/finclaw"))
    print()
