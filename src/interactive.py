"""
FinClaw Interactive Mode v2.6.0
REPL-style interactive session for exploratory analysis.
"""

import os
import sys
import json
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class InteractiveSession:
    """Interactive REPL for FinClaw analysis."""

    def __init__(self):
        self.data = None      # Current DataFrame
        self.ticker = None
        self.results = {}     # Store analysis results
        self.backtest_result = None
        self.trades = []

    def run(self):
        """Main REPL loop."""
        print("\n  FinClaw Interactive Mode v2.6.0")
        print("  Type 'help' for commands, 'quit' to exit.\n")

        while True:
            try:
                line = input("finclaw> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Bye!")
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                if cmd in ("quit", "exit", "q"):
                    print("  Bye!")
                    break
                elif cmd == "help":
                    self._help()
                elif cmd == "load":
                    self._load(args)
                elif cmd == "ta":
                    self._ta(args)
                elif cmd == "plot":
                    self._plot(args)
                elif cmd == "backtest":
                    self._backtest(args)
                elif cmd == "show":
                    self._show(args)
                elif cmd == "compare":
                    self._compare(args)
                elif cmd == "export":
                    self._export(args)
                elif cmd == "price":
                    self._price(args)
                elif cmd == "info":
                    self._info()
                else:
                    print(f"  Unknown command: {cmd}. Type 'help' for commands.")
            except Exception as e:
                print(f"  Error: {e}")

    def _help(self):
        print("""
  Commands:
    load <TICKER> [start] [end]   Load price data
    ta <indicator>                Technical analysis (rsi, macd, bollinger, sma20, ema20)
    plot                          Show price summary (text-based)
    backtest <strategy>           Run backtest on loaded data
    show trades                   Show trade log from backtest
    compare <strategy>            Compare with another strategy (buy_and_hold, momentum)
    export <file>                 Export results to file
    price <TICKER,...>            Quick price lookup
    info                          Show loaded data info
    quit                          Exit
""")

    def _load(self, args):
        if not args:
            print("  Usage: load TICKER [start_date] [end_date]")
            return

        self.ticker = args[0].upper()
        start = args[1] if len(args) > 1 else None
        end = args[2] if len(args) > 2 else None

        print(f"  Loading {self.ticker}...", end="", flush=True)

        try:
            import yfinance as yf
            import warnings, logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                stock = yf.Ticker(self.ticker)
                if start:
                    self.data = stock.history(start=start, end=end)
                else:
                    self.data = stock.history(period="1y")
        except Exception as e:
            print(f" failed: {e}")
            return

        if self.data is None or len(self.data) == 0:
            print(f" no data found.")
            self.data = None
            return

        print(f" {len(self.data)} bars loaded.")
        close = self.data["Close"]
        print(f"  Range: {close.index[0].date()} to {close.index[-1].date()}")
        print(f"  Price: {close.iloc[-1]:.2f} (Open: {close.iloc[0]:.2f}, Change: {close.iloc[-1]/close.iloc[0]-1:+.2%})")
        self.results = {}
        self.backtest_result = None

    def _ta(self, args):
        if self.data is None:
            print("  No data loaded. Use 'load TICKER' first.")
            return
        if not args:
            print("  Usage: ta <rsi|macd|bollinger|sma20|ema20>")
            return

        import numpy as np
        from src.ta import rsi as calc_rsi, macd as calc_macd, sma, ema

        close = np.array(self.data["Close"].tolist(), dtype=np.float64)
        ind = args[0].lower()

        if ind == "rsi":
            r = calc_rsi(close, 14)
            val = r[-1]
            self.results["rsi"] = float(val)
            signal = "OVERSOLD" if val < 30 else "OVERBOUGHT" if val > 70 else "NEUTRAL"
            print(f"  RSI(14): {val:.1f} — {signal}")
        elif ind == "macd":
            line, signal, hist = calc_macd(close)
            self.results["macd"] = {"line": float(line[-1]), "signal": float(signal[-1]), "hist": float(hist[-1])}
            trend = "BULLISH" if hist[-1] > 0 else "BEARISH"
            print(f"  MACD: {line[-1]:.2f} | Signal: {signal[-1]:.2f} | Hist: {hist[-1]:.2f} — {trend}")
        elif ind in ("bollinger", "bb"):
            sma20 = sma(close, 20)
            std = np.array([np.std(close[max(0, i - 19):i + 1]) for i in range(len(close))])
            upper = sma20 + 2 * std
            lower = sma20 - 2 * std
            self.results["bollinger"] = {"upper": float(upper[-1]), "mid": float(sma20[-1]), "lower": float(lower[-1])}
            print(f"  Bollinger: Upper={upper[-1]:.2f} Mid={sma20[-1]:.2f} Lower={lower[-1]:.2f}")
        elif ind.startswith("sma"):
            period = int(ind[3:]) if len(ind) > 3 else 20
            s = sma(close, period)
            self.results[f"sma{period}"] = float(s[-1])
            print(f"  SMA({period}): {s[-1]:.2f}")
        elif ind.startswith("ema"):
            period = int(ind[3:]) if len(ind) > 3 else 20
            e = ema(close, period)
            self.results[f"ema{period}"] = float(e[-1])
            print(f"  EMA({period}): {e[-1]:.2f}")
        else:
            print(f"  Unknown indicator: {ind}")

    def _plot(self, args):
        if self.data is None:
            print("  No data loaded.")
            return

        close = self.data["Close"].tolist()
        n = min(len(close), 60)
        recent = close[-n:]
        hi, lo = max(recent), min(recent)
        width = 50

        print(f"\n  {self.ticker} — Last {n} days")
        print(f"  High: {hi:.2f}  Low: {lo:.2f}")
        print()

        for i, p in enumerate(recent):
            bar_len = int((p - lo) / (hi - lo) * width) if hi != lo else width // 2
            bar = "█" * bar_len
            print(f"  {p:>8.2f} |{bar}")
        print()

    def _backtest(self, args):
        if self.data is None:
            print("  No data loaded.")
            return

        import asyncio
        from agents.backtester_v7 import BacktesterV7
        from datetime import datetime

        h = [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
              "volume": float(row.get("Volume", 0))}
             for idx, row in self.data.iterrows()]

        strategy = args[0] if args else "momentum"
        bt = BacktesterV7(initial_capital=100000)
        r = asyncio.run(bt.run(self.ticker, "v7", h))

        prices = [x["price"] for x in h]
        bh = prices[-1] / prices[0] - 1
        years = max(len(prices) / 252, 0.5)
        ann = (1 + r.total_return) ** (1 / years) - 1 if r.total_return > -1 else -1

        self.backtest_result = {
            "ticker": self.ticker, "strategy": strategy,
            "total_return": r.total_return, "annualized": ann,
            "max_drawdown": r.max_drawdown, "trades": r.total_trades,
            "win_rate": r.win_rate, "buy_hold": bh,
        }

        print(f"\n  Backtest: {self.ticker} | {strategy}")
        print(f"  Return: {r.total_return:+.1%} ({ann:+.1%}/yr) | B&H: {bh:+.1%}")
        print(f"  Alpha: {r.total_return - bh:+.1%} | MaxDD: {r.max_drawdown:+.1%}")
        print(f"  Trades: {r.total_trades} | Win Rate: {r.win_rate:.0%}")

    def _show(self, args):
        if not args:
            print("  Usage: show trades")
            return
        if args[0] == "trades":
            if self.backtest_result:
                print(f"  Backtest: {self.backtest_result['ticker']} | {self.backtest_result['strategy']}")
                print(f"  {self.backtest_result['trades']} trades, {self.backtest_result['win_rate']:.0%} win rate")
            else:
                print("  No backtest results. Run 'backtest' first.")

    def _compare(self, args):
        if self.data is None:
            print("  No data loaded.")
            return

        strategy = args[0] if args else "buy_and_hold"
        close = self.data["Close"].tolist()
        bh = close[-1] / close[0] - 1

        print(f"\n  Comparison: {strategy}")
        print(f"  Buy & Hold: {bh:+.1%}")
        if self.backtest_result:
            print(f"  Backtest:   {self.backtest_result['total_return']:+.1%}")
            diff = self.backtest_result['total_return'] - bh
            print(f"  Difference: {diff:+.1%} ({'outperforms' if diff > 0 else 'underperforms'})")

    def _export(self, args):
        if not args:
            print("  Usage: export <filename>")
            return

        filepath = args[0]
        export_data = {
            "ticker": self.ticker,
            "results": self.results,
            "backtest": self.backtest_result,
        }

        if filepath.endswith(".html"):
            try:
                from src.reports.html_report import generate_html_report
                data = self.backtest_result or {"ticker": self.ticker, "total_return": 0}
                data["equity_curve"] = self.data["Close"].tolist() if self.data is not None else []
                generate_html_report(data, title=f"FinClaw - {self.ticker}", output_path=filepath)
                print(f"  ✓ Exported to {filepath}")
            except Exception as e:
                print(f"  Export failed: {e}")
        else:
            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2, default=str)
            print(f"  ✓ Exported to {filepath}")

    def _price(self, args):
        if not args:
            print("  Usage: price AAPL,MSFT")
            return

        tickers = args[0].split(",")
        for ticker in tickers:
            try:
                import yfinance as yf
                import warnings, logging
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df = yf.Ticker(ticker.strip()).history(period="5d")
                if len(df) > 0:
                    price = float(df["Close"].iloc[-1])
                    change = price / float(df["Close"].iloc[-2]) - 1 if len(df) > 1 else 0
                    print(f"  {ticker.strip()}: {price:.2f} ({change:+.2%})")
                else:
                    print(f"  {ticker.strip()}: no data")
            except Exception as e:
                print(f"  {ticker.strip()}: error - {e}")

    def _info(self):
        if self.data is None:
            print("  No data loaded.")
            return
        close = self.data["Close"]
        print(f"\n  Ticker: {self.ticker}")
        print(f"  Bars: {len(self.data)}")
        print(f"  Range: {close.index[0].date()} to {close.index[-1].date()}")
        print(f"  Price: {close.iloc[-1]:.2f}")
        print(f"  High: {close.max():.2f} | Low: {close.min():.2f}")
        if self.results:
            print(f"  Indicators: {', '.join(self.results.keys())}")
        if self.backtest_result:
            print(f"  Backtest: {self.backtest_result['total_return']:+.1%}")


if __name__ == "__main__":
    InteractiveSession().run()
