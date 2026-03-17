#!/usr/bin/env python3
"""
Crypto RSI Strategy — FinClaw Example
=====================================
Buy BTC when RSI(14) < 30 (oversold), sell when RSI > 70 (overbought).
Uses Yahoo Finance for BTC-USD data (no API key needed).

Usage:
    python examples/crypto_rsi.py
    python examples/crypto_rsi.py ETH-USD
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def fetch(symbol: str = "BTC-USD", period: str = "1y"):
    import yfinance as yf
    import warnings, logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return yf.Ticker(symbol).history(period=period)


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
    out[:n] = 50
    return out


def run(symbol="BTC-USD", period="1y", capital=10_000):
    df = fetch(symbol, period)
    if df is None or len(df) < 30:
        print(f"Not enough data for {symbol}")
        return

    close = np.array(df["Close"].tolist(), dtype=np.float64)
    rsi14 = rsi(close)

    position = 0.0  # BTC amount (fractional)
    cash = capital
    trades = []
    oversold_threshold = 30
    overbought_threshold = 70

    for i in range(14, len(close)):
        if position == 0 and rsi14[i] < oversold_threshold:
            # Buy with all cash
            position = cash / close[i]
            cash = 0
            trades.append(("BUY", i, close[i], position))
        elif position > 0 and rsi14[i] > overbought_threshold:
            # Sell all
            cash = position * close[i]
            trades.append(("SELL", i, close[i], position))
            position = 0

    portfolio = cash + position * close[-1]
    ret = portfolio / capital - 1
    bh = close[-1] / close[0] - 1

    print(f"\n  🪙 Crypto RSI Strategy: {symbol}")
    print(f"  RSI thresholds: Buy < {oversold_threshold}, Sell > {overbought_threshold}")
    print(f"  Return: {ret:+.1%}  |  Buy&Hold: {bh:+.1%}  |  Alpha: {ret - bh:+.1%}")
    print(f"  Trades: {len(trades)}")
    print(f"  Final:  ${portfolio:,.0f} (from ${capital:,.0f})\n")


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC-USD"
    run(symbol)
