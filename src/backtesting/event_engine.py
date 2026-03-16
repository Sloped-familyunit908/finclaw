"""Event-Driven Backtesting Engine for FinClaw.

Provides a flexible, event-driven backtester that processes:
MarketEvent → Strategy → SignalEvent → OrderEvent → Execution → FillEvent → Portfolio
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    MARKET = "market"
    SIGNAL = "signal"
    ORDER = "order"
    FILL = "fill"


@dataclass
class Event:
    event_type: EventType = EventType.MARKET
    timestamp: Any = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketEvent(Event):
    """Emitted for each bar of market data."""
    symbol: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0

    def __post_init__(self):
        self.event_type = EventType.MARKET


@dataclass
class SignalEvent(Event):
    """Strategy-generated signal."""
    symbol: str = ""
    signal: float = 0.0  # +1 buy, -1 sell, 0 flat
    strength: float = 1.0

    def __post_init__(self):
        self.event_type = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    """Order to be executed."""
    symbol: str = ""
    quantity: float = 0.0
    side: str = "buy"  # buy / sell
    order_type: str = "market"
    limit_price: Optional[float] = None
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        self.event_type = EventType.ORDER


@dataclass
class FillEvent(Event):
    """Execution fill report."""
    symbol: str = ""
    quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    order_id: str = ""

    def __post_init__(self):
        self.event_type = EventType.FILL


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

@dataclass
class Portfolio:
    """Simple portfolio tracker."""
    initial_cash: float = 100_000.0
    cash: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_cash

    def update_fill(self, fill: FillEvent):
        cost = fill.fill_price * fill.quantity
        if fill.quantity > 0:  # buy
            self.cash -= cost + fill.commission
        else:  # sell
            self.cash -= cost + fill.commission  # quantity is negative → adds cash
        self.positions[fill.symbol] = self.positions.get(fill.symbol, 0) + fill.quantity
        self.trades.append({
            "symbol": fill.symbol,
            "quantity": fill.quantity,
            "price": fill.fill_price,
            "commission": fill.commission,
            "slippage": fill.slippage,
            "order_id": fill.order_id,
            "timestamp": fill.timestamp,
        })

    def mark_to_market(self, prices: Dict[str, float]):
        value = self.cash
        for sym, qty in self.positions.items():
            value += qty * prices.get(sym, 0.0)
        self.equity_curve.append(value)
        return value


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    equity_curve: List[float] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    num_trades: int = 0
    final_equity: float = 0.0

    @staticmethod
    def compute_max_drawdown(curve: List[float]) -> float:
        if not curve:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for v in curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd

    @staticmethod
    def compute_sharpe(curve: List[float], risk_free: float = 0.0) -> float:
        if len(curve) < 2:
            return 0.0
        returns = [(curve[i] - curve[i - 1]) / curve[i - 1]
                    for i in range(1, len(curve)) if curve[i - 1] != 0]
        if not returns:
            return 0.0
        import statistics
        mean_r = statistics.mean(returns) - risk_free / 252
        std_r = statistics.stdev(returns) if len(returns) > 1 else 1.0
        if std_r == 0:
            return 0.0
        return (mean_r / std_r) * (252 ** 0.5)


# ---------------------------------------------------------------------------
# Event-Driven Backtester
# ---------------------------------------------------------------------------

class EventDrivenBacktester:
    """Core event-driven backtesting engine.

    Usage:
        bt = EventDrivenBacktester()
        result = bt.run(data_df, strategy_fn,
                        slippage_fn=SlippageModel.fixed(5),
                        commission_fn=CommissionModel.percentage(0.001))
    """

    def __init__(self, initial_cash: float = 100_000.0):
        self.event_queue: List[Event] = []
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.initial_cash = initial_cash

    def register_handler(self, event_type: EventType, handler: Callable):
        self.handlers.setdefault(event_type, []).append(handler)

    def emit(self, event: Event):
        self.event_queue.append(event)

    def _drain_queue(self):
        while self.event_queue:
            event = self.event_queue.pop(0)
            for handler in self.handlers.get(event.event_type, []):
                handler(event)

    def run(
        self,
        data: pd.DataFrame,
        strategy: Callable[[MarketEvent, Portfolio], Optional[List[SignalEvent]]],
        slippage_fn: Optional[Callable[[float, float], float]] = None,
        commission_fn: Optional[Callable[[float, float], float]] = None,
        position_sizer: Optional[Callable[[SignalEvent, Portfolio, float], float]] = None,
    ) -> BacktestResult:
        """Run backtest on OHLCV DataFrame.

        Args:
            data: DataFrame with columns [open, high, low, close, volume] and optional 'symbol'.
            strategy: Callable(market_event, portfolio) -> list of SignalEvents or None.
            slippage_fn: Callable(price, quantity) -> adjusted_price.
            commission_fn: Callable(price, quantity) -> commission_amount.
            position_sizer: Callable(signal, portfolio, price) -> quantity.
        """
        portfolio = Portfolio(initial_cash=self.initial_cash)
        default_symbol = "ASSET"

        # Default slippage: no slippage
        if slippage_fn is None:
            slippage_fn = lambda price, qty: price

        # Default commission: zero
        if commission_fn is None:
            commission_fn = lambda price, qty: 0.0

        # Default position sizer: 10% of equity
        if position_sizer is None:
            def position_sizer(sig, port, price):
                equity = port.cash + sum(
                    qty * price for qty in port.positions.values()
                )
                return max(1, int(equity * 0.1 / price)) if price > 0 else 0

        # -- wire up handlers --
        def on_signal(event: SignalEvent):
            price = event.data.get("current_price", 0.0)
            if event.signal > 0:
                qty = position_sizer(event, portfolio, price)
                order = OrderEvent(
                    symbol=event.symbol, quantity=qty, side="buy",
                    timestamp=event.timestamp,
                )
                self.emit(order)
            elif event.signal < 0:
                held = portfolio.positions.get(event.symbol, 0)
                if held > 0:
                    order = OrderEvent(
                        symbol=event.symbol, quantity=-held, side="sell",
                        timestamp=event.timestamp,
                    )
                    self.emit(order)

        def on_order(event: OrderEvent):
            base_price = event.data.get("current_price", event.limit_price or 0.0)
            fill_price = slippage_fn(base_price, abs(event.quantity))
            commission = commission_fn(fill_price, abs(event.quantity))
            fill = FillEvent(
                symbol=event.symbol,
                quantity=event.quantity,
                fill_price=fill_price,
                commission=commission,
                slippage=abs(fill_price - base_price) * abs(event.quantity),
                order_id=event.order_id,
                timestamp=event.timestamp,
            )
            self.emit(fill)

        def on_fill(event: FillEvent):
            portfolio.update_fill(event)

        self.handlers.clear()
        self.register_handler(EventType.SIGNAL, on_signal)
        self.register_handler(EventType.ORDER, on_order)
        self.register_handler(EventType.FILL, on_fill)

        # -- iterate bars --
        for idx, row in data.iterrows():
            symbol = row.get("symbol", default_symbol) if isinstance(row, pd.Series) else default_symbol
            market = MarketEvent(
                symbol=symbol,
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                close=float(row.get("close", 0)),
                volume=float(row.get("volume", 0)),
                timestamp=idx,
            )

            # Strategy produces signals
            signals = strategy(market, portfolio)
            if signals:
                for sig in signals:
                    sig.data["current_price"] = market.close
                    sig.timestamp = market.timestamp
                    self.emit(sig)

            # Drain event queue (signals → orders → fills)
            self._drain_queue()

            # Mark to market
            portfolio.mark_to_market({symbol: market.close})

        # -- build result --
        curve = portfolio.equity_curve
        result = BacktestResult(
            equity_curve=curve,
            trades=portfolio.trades,
            total_return=((curve[-1] / curve[0]) - 1) if curve else 0.0,
            max_drawdown=BacktestResult.compute_max_drawdown(curve),
            sharpe_ratio=BacktestResult.compute_sharpe(curve),
            num_trades=len(portfolio.trades),
            final_equity=curve[-1] if curve else self.initial_cash,
        )
        return result
