"""
Strategy Runner - execute trading strategies in paper trading mode.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Callable, Protocol

from src.paper.engine import PaperTradingEngine


class Strategy(Protocol):
    """Protocol for trading strategies."""

    def on_tick(self, engine: PaperTradingEngine, symbols: list[str]) -> None:
        """Called on each tick with the engine and symbol list."""
        ...


class GoldenCrossStrategy:
    """Simple golden cross (SMA50 > SMA200) strategy."""

    name = "golden-cross"

    def __init__(self):
        self._history: dict[str, list[float]] = {}

    def on_tick(self, engine: PaperTradingEngine, symbols: list[str]) -> None:
        for symbol in symbols:
            price = engine._get_price(symbol)
            if price is None:
                continue

            if symbol not in self._history:
                self._history[symbol] = []
            self._history[symbol].append(price)

            prices = self._history[symbol]
            if len(prices) < 200:
                continue

            sma50 = sum(prices[-50:]) / 50
            sma200 = sum(prices[-200:]) / 200

            has_position = symbol in engine.positions

            if sma50 > sma200 and not has_position:
                # Buy signal
                affordable = int(engine.balance * 0.1 / price)
                if affordable > 0:
                    engine.buy(symbol, affordable)
            elif sma50 < sma200 and has_position:
                # Sell signal
                engine.sell(symbol, engine.positions[symbol].quantity)


class MomentumStrategy:
    """Simple momentum strategy - buy winners, sell losers."""

    name = "momentum"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self._history: dict[str, list[float]] = {}

    def on_tick(self, engine: PaperTradingEngine, symbols: list[str]) -> None:
        for symbol in symbols:
            price = engine._get_price(symbol)
            if price is None:
                continue

            if symbol not in self._history:
                self._history[symbol] = []
            self._history[symbol].append(price)

            prices = self._history[symbol]
            if len(prices) < self.lookback:
                continue

            ret = (prices[-1] / prices[-self.lookback] - 1)
            has_position = symbol in engine.positions

            if ret > 0.05 and not has_position:
                affordable = int(engine.balance * 0.1 / price)
                if affordable > 0:
                    engine.buy(symbol, affordable)
            elif ret < -0.03 and has_position:
                engine.sell(symbol, engine.positions[symbol].quantity)


BUILTIN_STRATEGIES: dict[str, type] = {
    "golden-cross": GoldenCrossStrategy,
    "momentum": MomentumStrategy,
}


class StrategyRunner:
    """Run a strategy in paper trading mode with periodic ticks."""

    def __init__(
        self,
        engine: PaperTradingEngine,
        strategy: Any,
        symbols: list[str] | None = None,
        interval: int = 60,
    ):
        self.engine = engine
        self.strategy = strategy
        self.symbols = symbols or []
        self.interval = interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._tick_count = 0
        self._start_time = 0.0
        self._errors: list[str] = []

    def start(self) -> None:
        """Start the strategy loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the strategy loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def tick(self) -> None:
        """Execute a single strategy tick (useful for testing)."""
        try:
            self.strategy.on_tick(self.engine, self.symbols)
            self._tick_count += 1
        except Exception as e:
            self._errors.append(str(e))

    def _run_loop(self) -> None:
        while self._running:
            self.tick()
            time.sleep(self.interval)

    @property
    def is_running(self) -> bool:
        return self._running

    def get_stats(self) -> dict:
        """Return runner statistics."""
        elapsed = time.time() - self._start_time if self._start_time else 0
        pnl = self.engine.get_pnl()
        return {
            "ticks": self._tick_count,
            "elapsed_seconds": elapsed,
            "trades": pnl.total_trades,
            "realized_pnl": pnl.realized,
            "unrealized_pnl": pnl.unrealized,
            "total_pnl": pnl.total,
            "win_rate": pnl.win_rate,
            "errors": len(self._errors),
            "is_running": self._running,
            "strategy": getattr(self.strategy, "name", type(self.strategy).__name__),
        }
