"""
FinClaw Interactive REPL v5.7.0
Rich interactive shell with tab completion, command history, and colored output.

Usage: finclaw shell
"""

import os
import sys
import shlex
import traceback
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.cli.formatter import OutputFormatter


# Well-known symbols for tab completion
POPULAR_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META",
    "SPY", "QQQ", "IWM", "DIA", "GLD", "SLV",
    "EURUSD=X", "GBPUSD=X", "USDJPY=X",
]

COMMANDS = [
    "quote", "load", "ta", "backtest", "portfolio", "watchlist",
    "alert", "screener", "compare", "export", "show", "plot",
    "price", "info", "config", "help", "quit", "exit", "clear",
]

INDICATORS = ["rsi", "macd", "bollinger", "sma20", "sma50", "ema20", "ema50"]

STRATEGIES = ["momentum", "mean_reversion", "grid_trading", "trend_following", "buy_and_hold"]


class _Completer:
    """Tab completer for the REPL."""

    def __init__(self):
        self.options = []

    def complete(self, text: str, state: int):
        if state == 0:
            line = ""
            try:
                import readline
                line = readline.get_line_buffer()
            except Exception:
                pass

            parts = line.lstrip().split()
            if len(parts) <= 1:
                # Complete command
                self.options = [c + " " for c in COMMANDS if c.startswith(text)]
            else:
                cmd = parts[0].lower()
                if cmd in ("quote", "load", "price", "compare"):
                    self.options = [s for s in POPULAR_SYMBOLS if s.startswith(text.upper())]
                elif cmd == "ta":
                    self.options = [i for i in INDICATORS if i.startswith(text.lower())]
                elif cmd == "backtest":
                    self.options = [s for s in STRATEGIES if s.startswith(text.lower())]
                else:
                    self.options = []

        return self.options[state] if state < len(self.options) else None


def _setup_readline() -> bool:
    """Set up readline with history and tab completion. Returns True if available."""
    try:
        import readline
    except ImportError:
        try:
            import pyreadline3 as readline
        except ImportError:
            return False

    completer = _Completer()
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")

    # History file
    hist_path = os.path.expanduser("~/.finclaw/history")
    os.makedirs(os.path.dirname(hist_path), exist_ok=True)
    try:
        readline.read_history_file(hist_path)
    except FileNotFoundError:
        pass

    import atexit
    atexit.register(readline.write_history_file, hist_path)
    return True


class FinClawREPL:
    """Interactive REPL for FinClaw.

    Features:
    - Tab completion for commands, symbols, exchanges
    - Command history (~/.finclaw/history)
    - Colored output with quote cards and sparklines
    - All major FinClaw commands available
    """

    def __init__(self):
        self.data = None
        self.ticker = None
        self.results: Dict[str, Any] = {}
        self.backtest_result = None
        self.fmt = OutputFormatter
        self._has_readline = False

    def run(self) -> None:
        """Main REPL loop."""
        self._has_readline = _setup_readline()
        self._print_banner()

        while True:
            try:
                prompt = self.fmt.color("finclaw", "bright_cyan") + self.fmt.color("> ", "white")
                line = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {self.fmt.color('Bye! 🦀', 'cyan')}")
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                handler = self._get_handler(cmd)
                if handler:
                    handler(args)
                else:
                    print(f"  Unknown command: {cmd}. Type 'help' for commands.")
            except Exception as e:
                print(f"  {self.fmt.color('Error:', 'red')} {e}")

    def _print_banner(self) -> None:
        banner = r"""
   _____ _       ____ _
  |  ___(_)_ __ / ___| | __ ___      __
  | |_  | | '_ \ |   | |/ _` \ \ /\ / /
  |  _| | | | | | |___| | (_| |\ V  V /
  |_|   |_|_| |_|\____|_|\__,_| \_/\_/
"""
        print(self.fmt.color(banner, "bright_cyan"))
        print(f"  {self.fmt.bold('FinClaw Interactive Shell v5.7.0')}")
        features = []
        if self._has_readline:
            features.append("Tab completion ✓")
            features.append("History ✓")
        print(f"  {' | '.join(features)}" if features else "")
        print(f"  Type {self.fmt.color('help', 'yellow')} for commands, {self.fmt.color('quit', 'yellow')} to exit.\n")

    def _get_handler(self, cmd: str) -> Optional[Callable]:
        handlers = {
            "help": self._cmd_help,
            "quit": self._cmd_quit,
            "exit": self._cmd_quit,
            "q": self._cmd_quit,
            "clear": self._cmd_clear,
            "quote": self._cmd_quote,
            "load": self._cmd_load,
            "ta": self._cmd_ta,
            "plot": self._cmd_plot,
            "backtest": self._cmd_backtest,
            "show": self._cmd_show,
            "compare": self._cmd_compare,
            "export": self._cmd_export,
            "price": self._cmd_price,
            "info": self._cmd_info,
            "config": self._cmd_config,
            "portfolio": self._cmd_portfolio,
            "watchlist": self._cmd_watchlist,
        }
        return handlers.get(cmd)

    def _cmd_help(self, args: List[str]) -> None:
        sections = {
            "Data": [
                ("quote <SYMBOL>", "Quick quote with card display"),
                ("price <SYM1,SYM2>", "Multi-symbol price check"),
                ("load <SYMBOL> [start] [end]", "Load historical data"),
                ("info", "Show loaded data info"),
            ],
            "Analysis": [
                ("ta <indicator>", "Technical analysis (rsi, macd, bollinger, sma, ema)"),
                ("plot", "Text-based price chart"),
                ("compare <strategy>", "Compare strategies"),
            ],
            "Trading": [
                ("backtest <strategy>", "Run backtest on loaded data"),
                ("show trades", "Show trade log"),
                ("portfolio status", "Portfolio overview"),
                ("watchlist", "Manage watchlist"),
            ],
            "System": [
                ("config [key] [value]", "View/set configuration"),
                ("export <file>", "Export results"),
                ("clear", "Clear screen"),
                ("help", "Show this help"),
                ("quit", "Exit shell"),
            ],
        }

        print()
        for section, cmds in sections.items():
            print(f"  {self.fmt.bold(section)}")
            for cmd, desc in cmds:
                print(f"    {self.fmt.color(cmd.ljust(32), 'cyan')}{desc}")
            print()

    def _cmd_quit(self, args: List[str]) -> None:
        print(f"  {self.fmt.color('Bye! 🦀', 'cyan')}")
        raise SystemExit(0)

    def _cmd_clear(self, args: List[str]) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _cmd_quote(self, args: List[str]) -> None:
        if not args:
            print("  Usage: quote BTCUSDT")
            return

        symbol = args[0].upper()
        print(f"  Fetching {symbol}...", end="", flush=True)

        try:
            import yfinance as yf
            import warnings, logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

            if hist.empty:
                print(f" no data.")
                return

            price = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
            change_pct = (price / prev - 1) * 100
            volume = float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else None
            high = float(hist["High"].iloc[-1]) if "High" in hist.columns else None
            low = float(hist["Low"].iloc[-1]) if "Low" in hist.columns else None

            print("\r" + " " * 40 + "\r", end="")  # Clear "Fetching..."
            card = self.fmt.quote_card({
                "symbol": symbol,
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "high": high,
                "low": low,
            })
            print(f"\n{card}\n")

            # Show sparkline of recent closes
            if len(hist) >= 3:
                closes = hist["Close"].tolist()
                spark = self.fmt.sparkline(closes)
                print(f"  5-day: {spark}\n")

        except Exception as e:
            print(f" error: {e}")

    def _cmd_load(self, args: List[str]) -> None:
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

        close = self.data["Close"]
        n = len(self.data)
        change = close.iloc[-1] / close.iloc[0] - 1
        spark = self.fmt.sparkline(close.tolist(), width=20)

        print(f" {self.fmt.color(f'{n} bars', 'green')} loaded.")
        print(f"  {close.index[0].date()} → {close.index[-1].date()}")
        print(f"  Price: {self.fmt.bold(f'{close.iloc[-1]:.2f}')}  Change: {self.fmt.price_color(change)}")
        print(f"  {spark}")
        self.results = {}
        self.backtest_result = None

    def _cmd_ta(self, args: List[str]) -> None:
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
            if val < 30:
                signal = self.fmt.color("OVERSOLD", "bright_green")
            elif val > 70:
                signal = self.fmt.color("OVERBOUGHT", "bright_red")
            else:
                signal = self.fmt.color("NEUTRAL", "yellow")
            bar = self.fmt.progress_bar(val, 100, width=20, show_pct=False)
            print(f"  RSI(14): {val:.1f} {bar} {signal}")
        elif ind == "macd":
            line, signal_line, hist = calc_macd(close)
            self.results["macd"] = {"line": float(line[-1]), "signal": float(signal_line[-1]), "hist": float(hist[-1])}
            trend = self.fmt.color("BULLISH ▲", "bright_green") if hist[-1] > 0 else self.fmt.color("BEARISH ▼", "bright_red")
            print(f"  MACD: {line[-1]:.2f} | Signal: {signal_line[-1]:.2f} | Hist: {hist[-1]:.2f} — {trend}")
        elif ind in ("bollinger", "bb"):
            sma20 = sma(close, 20)
            std = np.array([np.std(close[max(0, i - 19):i + 1]) for i in range(len(close))])
            upper = sma20 + 2 * std
            lower = sma20 - 2 * std
            self.results["bollinger"] = {"upper": float(upper[-1]), "mid": float(sma20[-1]), "lower": float(lower[-1])}
            print(f"  Bollinger Bands:")
            print(f"    Upper: {upper[-1]:.2f}  Mid: {sma20[-1]:.2f}  Lower: {lower[-1]:.2f}")
            pos = (close[-1] - lower[-1]) / (upper[-1] - lower[-1]) if upper[-1] != lower[-1] else 0.5
            bar = self.fmt.progress_bar(pos, 1.0, width=20, label="  Position:", show_pct=True)
            print(bar)
        else:
            # Generic SMA/EMA
            if ind.startswith("sma"):
                period = int(ind[3:]) if len(ind) > 3 else 20
                s = sma(close, period)
                self.results[f"sma{period}"] = float(s[-1])
                print(f"  SMA({period}): {self.fmt.bold(f'{s[-1]:.2f}')}")
            elif ind.startswith("ema"):
                period = int(ind[3:]) if len(ind) > 3 else 20
                e = ema(close, period)
                self.results[f"ema{period}"] = float(e[-1])
                print(f"  EMA({period}): {self.fmt.bold(f'{e[-1]:.2f}')}")
            else:
                print(f"  Unknown indicator: {ind}")

    def _cmd_plot(self, args: List[str]) -> None:
        if self.data is None:
            print("  No data loaded.")
            return

        close = self.data["Close"].tolist()
        n = min(len(close), 60)
        recent = close[-n:]
        hi, lo = max(recent), min(recent)
        width = 50

        print(f"\n  {self.fmt.bold(self.ticker)} — Last {n} days")
        print(f"  {self.fmt.color(f'High: {hi:.2f}', 'green')}  {self.fmt.color(f'Low: {lo:.2f}', 'red')}")
        print()

        for p in recent:
            bar_len = int((p - lo) / (hi - lo) * width) if hi != lo else width // 2
            bar = "█" * bar_len
            color = "bright_green" if p >= recent[0] else "bright_red"
            print(f"  {p:>8.2f} │{self.fmt.color(bar, color)}")
        print()

    def _cmd_backtest(self, args: List[str]) -> None:
        if self.data is None:
            print("  No data loaded.")
            return

        import asyncio
        from agents.backtester_v7 import BacktesterV7

        h = [{"date": idx.to_pydatetime(), "price": float(row["Close"]),
              "volume": float(row.get("Volume", 0))}
             for idx, row in self.data.iterrows()]

        strategy = args[0] if args else "momentum"
        print(f"  Running {self.fmt.bold(strategy)} backtest...", end="", flush=True)

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

        print("\r" + " " * 50 + "\r", end="")
        print()
        headers = ["Metric", "Value"]
        alpha = r.total_return - bh
        rows = [
            ["Strategy", strategy],
            ["Return", f"{r.total_return:+.1%}"],
            ["Annualized", f"{ann:+.1%}"],
            ["Buy & Hold", f"{bh:+.1%}"],
            ["Alpha", f"{alpha:+.1%}"],
            ["Max Drawdown", f"{r.max_drawdown:+.1%}"],
            ["Trades", str(r.total_trades)],
            ["Win Rate", f"{r.win_rate:.0%}"],
        ]
        print(self.fmt.table(headers, rows, style="compact"))

    def _cmd_show(self, args: List[str]) -> None:
        if not args:
            print("  Usage: show trades")
            return
        if args[0] == "trades":
            if self.backtest_result:
                print(self.fmt.key_value(self.backtest_result))
            else:
                print("  No backtest results. Run 'backtest' first.")

    def _cmd_compare(self, args: List[str]) -> None:
        if self.data is None:
            print("  No data loaded.")
            return

        close = self.data["Close"].tolist()
        bh = close[-1] / close[0] - 1
        print(f"\n  Buy & Hold: {self.fmt.price_color(bh)}")
        if self.backtest_result:
            ret = self.backtest_result["total_return"]
            print(f"  Strategy:   {self.fmt.price_color(ret)}")
            diff = ret - bh
            label = self.fmt.color("outperforms", "bright_green") if diff > 0 else self.fmt.color("underperforms", "bright_red")
            print(f"  Alpha:      {self.fmt.price_color(diff)} ({label})")

    def _cmd_export(self, args: List[str]) -> None:
        if not args:
            print("  Usage: export <filename>")
            return
        import json
        filepath = args[0]
        data = {
            "ticker": self.ticker,
            "results": self.results,
            "backtest": self.backtest_result,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"  ✓ Exported to {filepath}")

    def _cmd_price(self, args: List[str]) -> None:
        if not args:
            print("  Usage: price AAPL,MSFT,BTCUSDT")
            return

        tickers = args[0].split(",")
        for t in tickers:
            try:
                import yfinance as yf
                import warnings, logging
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df = yf.Ticker(t.strip()).history(period="5d")
                if len(df) > 0:
                    price = float(df["Close"].iloc[-1])
                    prev = float(df["Close"].iloc[-2]) if len(df) > 1 else price
                    change = price / prev - 1
                    spark = self.fmt.sparkline(df["Close"].tolist())
                    print(f"  {t.strip():8s} {price:>10.2f} {self.fmt.price_color(change):>12s} {spark}")
                else:
                    print(f"  {t.strip()}: no data")
            except Exception as e:
                print(f"  {t.strip()}: error - {e}")

    def _cmd_info(self, args: List[str]) -> None:
        if self.data is None:
            print("  No data loaded.")
            return
        close = self.data["Close"]
        data = {
            "Ticker": self.ticker,
            "Bars": len(self.data),
            "Range": f"{close.index[0].date()} → {close.index[-1].date()}",
            "Price": f"{close.iloc[-1]:.2f}",
            "High": f"{close.max():.2f}",
            "Low": f"{close.min():.2f}",
        }
        if self.results:
            data["Indicators"] = ", ".join(self.results.keys())
        if self.backtest_result:
            data["Backtest"] = f"{self.backtest_result['total_return']:+.1%}"
        print()
        print(self.fmt.key_value(data))
        print()

    def _cmd_config(self, args: List[str]) -> None:
        from src.cli.config import ConfigManager
        config = ConfigManager()
        if not args:
            import json
            print(json.dumps(config.to_dict(), indent=2))
        elif len(args) == 1:
            val = config.get(args[0])
            print(f"  {args[0]} = {val}")
        elif len(args) >= 2:
            config.set(args[0], args[1])
            config.save()
            print(f"  ✓ {args[0]} = {args[1]}")

    def _cmd_portfolio(self, args: List[str]) -> None:
        print("  Portfolio feature coming soon. Use 'backtest' for now.")

    def _cmd_watchlist(self, args: List[str]) -> None:
        print("  Watchlist feature coming soon. Use 'quote <SYMBOL>' for now.")


def main():
    """Entry point for finclaw shell."""
    repl = FinClawREPL()
    repl.run()


if __name__ == "__main__":
    main()
