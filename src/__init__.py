# FinClaw - AI-native quantitative finance platform
"""FinClaw - AI-native quantitative finance engine."""

__version__ = "5.1.0"


class FinClaw:
    """High-level convenience API for FinClaw.

    Examples::

        from finclaw import FinClaw

        fc = FinClaw()
        quote = fc.quote("AAPL")
        print(f"AAPL: ${quote['price']:.2f} ({quote['change_pct']:+.1f}%)")
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}

    # ── Quotes ──────────────────────────────────────────────────

    def quote(self, symbol: str) -> dict:
        """Get a real-time quote for *symbol* via Yahoo Finance.

        Returns a dict with keys: symbol, price, change, change_pct, volume,
        high, low, open, previous_close.
        """
        from src.exchanges.yahoo_finance import YahooFinanceAdapter

        adapter = YahooFinanceAdapter()
        ticker = adapter.get_ticker(symbol)
        return {
            "symbol": ticker.get("symbol", symbol),
            "price": ticker.get("last", 0),
            "change": ticker.get("change", 0),
            "change_pct": ticker.get("change_pct", 0),
            "volume": ticker.get("volume", 0),
            "high": ticker.get("high", 0),
            "low": ticker.get("low", 0),
            "open": ticker.get("open", 0),
            "previous_close": ticker.get("previous_close", 0),
        }

    # ── Backtesting ─────────────────────────────────────────────

    def backtest(
        self,
        strategy: str = "momentum",
        ticker: str = "AAPL",
        start: str = "2020-01-01",
        end: str | None = None,
        capital: float = 100_000,
    ) -> dict:
        """Run a backtest and return a result dict.

        Returns dict with: total_return, sharpe_ratio, max_drawdown,
        win_rate, total_trades, annualized_return, final_equity.
        """
        import asyncio
        from src.cli.main import _fetch_data

        df = _fetch_data(ticker, start=start, end=end)
        if df is None or len(df) < 2:
            raise ValueError(f"No data available for {ticker}")

        prices = df["Close"].tolist()
        from datetime import datetime as _dt

        history = [
            {
                "date": idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx,
                "price": float(row["Close"]),
                "volume": float(row.get("Volume", 0)),
            }
            for idx, row in df.iterrows()
        ]

        from agents.backtester_v7 import BacktesterV7

        bt = BacktesterV7(initial_capital=capital)
        r = asyncio.run(bt.run(ticker, "v7", history))
        years = max(len(prices) / 252, 0.5)
        ann = (1 + r.total_return) ** (1 / years) - 1 if r.total_return > -1 else -1
        buy_hold = prices[-1] / prices[0] - 1

        class _Result:
            def __init__(self, d):
                self.__dict__.update(d)

            def export_html(self, path: str):
                from src.reports.html_report import generate_html_report
                generate_html_report(self.__dict__, output_path=path)

        return _Result(
            {
                "total_return": r.total_return,
                "annualized_return": ann,
                "sharpe_ratio": getattr(r, "sharpe_ratio", 0),
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "total_trades": r.total_trades,
                "buy_hold": buy_hold,
                "final_equity": capital * (1 + r.total_return),
            }
        )

    # ── Paper trading ───────────────────────────────────────────

    def paper_trade(
        self,
        strategy: str = "trend",
        symbols: list[str] | None = None,
        capital: float = 100_000,
    ):
        """Start a paper-trading session (blocking)."""
        from src.paper.engine import PaperTradingEngine
        from src.paper.runner import StrategyRunner, BUILTIN_STRATEGIES

        symbols = symbols or ["AAPL"]
        engine = PaperTradingEngine(initial_balance=capital)
        if strategy in BUILTIN_STRATEGIES:
            strat = BUILTIN_STRATEGIES[strategy]()
            runner = StrategyRunner(engine, strat, symbols=symbols)
            runner.run()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")


__all__ = ["__version__", "FinClaw"]
