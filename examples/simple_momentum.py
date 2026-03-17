#!/usr/bin/env python3
"""
Simple Momentum Strategy — FinClaw Example
==========================================
Buy when price is above 20-day SMA and RSI > 50.
Sell when price drops below 20-day SMA.

Usage:
    python examples/simple_momentum.py
    # Or via CLI:
    finclaw backtest --strategy momentum --ticker AAPL
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from src.data.cache import DataCache


def fetch(ticker: str, period: str = "2y"):
    """Fetch data via yfinance."""
    import yfinance as yf
    import warnings, logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return yf.Ticker(ticker).history(period=period)


def sma(prices, n):
    out = np.full_like(prices, np.nan)
    for i in range(n - 1, len(prices)):
        out[i] = np.mean(prices[i - n + 1 : i + 1])
    return out


def rsi(prices, n=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.zeros(len(prices))
    avg_loss = np.zeros(len(prices))
    avg_gain[n] = np.mean(gains[:n])
    avg_loss[n] = np.mean(losses[:n])
    for i in range(n + 1, len(prices)):
        avg_gain[i] = (avg_gain[i - 1] * (n - 1) + gains[i - 1]) / n
        avg_loss[i] = (avg_loss[i - 1] * (n - 1) + losses[i - 1]) / n
    rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100.0)
    out = 100 - 100 / (1 + rs)
    out[:n] = 50  # fill initial values
    return out


def run(ticker="AAPL", period="2y", capital=100_000):
    df = fetch(ticker, period)
    if df is None or len(df) < 30:
        print(f"Not enough data for {ticker}")
        return

    close = np.array(df["Close"].tolist(), dtype=np.float64)
    sma20 = sma(close, 20)
    rsi14 = rsi(close)

    # Strategy: buy when close > SMA(20) and RSI > 50
    position = 0
    entry_price = 0
    cash = capital
    trades = []

    for i in range(20, len(close)):
        if position == 0 and close[i] > sma20[i] and rsi14[i] > 50:
            shares = int(cash / close[i])
            if shares > 0:
                entry_price = close[i]
                position = shares
                cash -= shares * close[i]
                trades.append(("BUY", i, close[i], shares))
        elif position > 0 and close[i] < sma20[i]:
            cash += position * close[i]
            pnl = (close[i] - entry_price) * position
            trades.append(("SELL", i, close[i], position, pnl))
            position = 0

    # Mark to market
    portfolio_value = cash + position * close[-1]
    total_return = portfolio_value / capital - 1
    bh_return = close[-1] / close[0] - 1

    print(f"\n  🚀 Simple Momentum Strategy: {ticker}")
    print(f"  Period: {period} ({len(close)} days)")
    print(f"  Return: {total_return:+.1%}  |  Buy&Hold: {bh_return:+.1%}  |  Alpha: {total_return - bh_return:+.1%}")
    print(f"  Trades: {len(trades)}")
    print(f"  Final:  ${portfolio_value:,.0f} (from ${capital:,.0f})\n")


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    run(ticker)
