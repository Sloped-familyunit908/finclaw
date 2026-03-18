"""Event-Driven Backtesting Engine v5.6.0

Architecture: MarketEvent → Strategy → SignalEvent → OrderManager → OrderEvent → Execution → FillEvent → PositionTracker
"""

from __future__ import annotations

import math
import statistics
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from .orders import OrderManager, Order, OrderType, OrderSide, OrderStatus
from .positions import PositionTracker, PositionSide


# ---------------------------------------------------------------------------
# Events
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


@dataclass
class MarketEvent(Event):
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
    symbol: str = ""
    signal: float = 0.0  # +1 buy, -1 sell, 0 flat
    strength: float = 1.0
    target_quantity: Optional[float] = None
    target_price: Optional[float] = None

    def __post_init__(self):
        self.event_type = EventType.SIGNAL


@dataclass
class OrderEvent(Event):
    symbol: str = ""
    quantity: float = 0.0
    side: str = "buy"
    order_type: str = "market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    order_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self):
        self.event_type = EventType.ORDER


@dataclass
class FillEvent(Event):
    symbol: str = ""
    quantity: float = 0.0
    fill_price: float = 0.0
    commission: float = 0.0
    slippage_cost: float = 0.0
    side: str = "buy"
    order_id: str = ""

    def __post_init__(self):
        self.event_type = EventType.FILL


# ---------------------------------------------------------------------------
# Strategy Protocol
# ---------------------------------------------------------------------------

class Strategy(Protocol):
    def on_market(self, event: MarketEvent, context: StrategyContext) -> Optional[List[SignalEvent]]:
        ...


@dataclass
class StrategyContext:
    """Read-only context passed to strategy."""
    cash: float = 0.0
    equity: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    prices: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# BacktestResult
# ---------------------------------------------------------------------------

@dataclass
class BacktestResult:
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    num_trades: int = 0
    final_equity: float = 0.0
    initial_capital: float = 0.0
    total_commission: float = 0.0
    total_slippage: float = 0.0

    @staticmethod
    def _compute_max_drawdown(curve: List[float]) -> float:
        if not curve:
            return 0.0
        peak = curve[0]
        max_dd = 0.0
        for v in curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
        return max_dd

    @staticmethod
    def _compute_returns(curve: List[float]) -> List[float]:
        if len(curve) < 2:
            return []
        return [(curve[i] - curve[i - 1]) / curve[i - 1]
                for i in range(1, len(curve)) if curve[i - 1] != 0]

    @staticmethod
    def _compute_sharpe(returns: List[float], risk_free: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = statistics.mean(returns) - risk_free / 252
        std_r = statistics.stdev(returns)
        if std_r == 0:
            return 0.0
        return (mean_r / std_r) * (252 ** 0.5)

    @staticmethod
    def _compute_sortino(returns: List[float], risk_free: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        mean_r = statistics.mean(returns) - risk_free / 252
        downside = [r for r in returns if r < 0]
        if not downside:
            return float('inf') if mean_r > 0 else 0.0
        down_std = math.sqrt(sum(r ** 2 for r in downside) / len(downside))
        if down_std == 0:
            return 0.0
        return (mean_r / down_std) * (252 ** 0.5)

    @staticmethod
    def _compute_cagr(initial: float, final: float, n_bars: int, bars_per_year: float = 252) -> float:
        if initial <= 0 or final <= 0 or n_bars <= 0:
            return 0.0
        years = n_bars / bars_per_year
        if years <= 0:
            return 0.0
        return (final / initial) ** (1 / years) - 1

    @staticmethod
    def _compute_win_rate(trades: List[Dict[str, Any]]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        return wins / len(trades)

    @staticmethod
    def _compute_profit_factor(trades: List[Dict[str, Any]]) -> float:
        gross_profit = sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t.get("pnl", 0) < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss


# ---------------------------------------------------------------------------
# BacktestEngine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Event-driven backtesting engine.

    Usage:
        engine = BacktestEngine(initial_capital=100000)
        engine.add_data("AAPL", ohlcv_list)
        engine.set_strategy(my_strategy)
        engine.set_commission(0.001)
        engine.set_slippage('fixed', 0.0001)
        result = engine.run()
    """

    def __init__(self, initial_capital: float = 100_000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.data: Dict[str, List[Dict[str, Any]]] = {}
        self.strategy: Optional[Any] = None
        self.commission_rate: float = 0.0
        self.slippage_model: str = "fixed"
        self.slippage_value: float = 0.0
        self.event_queue: List[Event] = []
        self.position_tracker = PositionTracker()
        self.order_manager = OrderManager()
        self.equity_curve: List[float] = []
        self.trades: List[Dict[str, Any]] = []
        self.current_prices: Dict[str, float] = {}
        self.total_commission: float = 0.0
        self.total_slippage: float = 0.0
        self._handlers: Dict[EventType, List[Callable]] = {
            EventType.MARKET: [],
            EventType.SIGNAL: [self._on_signal],
            EventType.ORDER: [self._on_order],
            EventType.FILL: [self._on_fill],
        }

    def add_data(self, symbol: str, data: list) -> None:
        """Add OHLCV data for a symbol. Each item: {open, high, low, close, volume, timestamp?}"""
        self.data[symbol] = data

    def set_strategy(self, strategy) -> None:
        """Set strategy. Must have on_market(event, context) -> Optional[List[SignalEvent]]"""
        self.strategy = strategy

    def set_commission(self, rate: float = 0.001) -> None:
        self.commission_rate = rate

    def set_slippage(self, model: str = "fixed", value: float = 0.0001) -> None:
        self.slippage_model = model
        self.slippage_value = value

    def _emit(self, event: Event):
        self.event_queue.append(event)

    def _drain(self):
        while self.event_queue:
            event = self.event_queue.pop(0)
            for handler in self._handlers.get(event.event_type, []):
                handler(event)

    def _apply_slippage(self, price: float, side: str) -> float:
        if self.slippage_model == "fixed":
            return price + self.slippage_value if side == "buy" else price - self.slippage_value
        elif self.slippage_model == "pct":
            return price * (1 + self.slippage_value) if side == "buy" else price * (1 - self.slippage_value)
        return price

    def _apply_commission(self, price: float, quantity: float) -> float:
        return abs(price * quantity * self.commission_rate)

    def _build_context(self) -> StrategyContext:
        positions = {}
        for sym in self.position_tracker.positions:
            pos = self.position_tracker.positions[sym]
            positions[sym] = pos.quantity if pos.side == PositionSide.LONG else -pos.quantity
        equity = self.cash + self.position_tracker.get_portfolio_value(self.current_prices)
        return StrategyContext(
            cash=self.cash,
            equity=equity,
            positions=positions,
            prices=dict(self.current_prices),
        )

    def _on_signal(self, event: SignalEvent):
        price = self.current_prices.get(event.symbol, 0.0)
        if price <= 0:
            return

        if event.signal > 0:
            qty = event.target_quantity
            if qty is None:
                equity = self.cash + self.position_tracker.get_portfolio_value(self.current_prices)
                qty = max(1, int(equity * 0.1 / price))
            order_evt = OrderEvent(
                symbol=event.symbol, quantity=qty, side="buy",
                order_type="market", timestamp=event.timestamp,
            )
            self._emit(order_evt)
        elif event.signal < 0:
            pos = self.position_tracker.positions.get(event.symbol)
            if pos and pos.quantity > 0:
                qty = event.target_quantity or pos.quantity
                order_evt = OrderEvent(
                    symbol=event.symbol, quantity=qty, side="sell",
                    order_type="market", timestamp=event.timestamp,
                )
                self._emit(order_evt)

    def _on_order(self, event: OrderEvent):
        fill_price = self._apply_slippage(
            self.current_prices.get(event.symbol, 0.0), event.side
        )
        commission = self._apply_commission(fill_price, event.quantity)

        # Check if we can afford this
        if event.side == "buy":
            cost = fill_price * event.quantity + commission
            if cost > self.cash:
                return  # Reject: insufficient funds

        fill = FillEvent(
            symbol=event.symbol,
            quantity=event.quantity,
            fill_price=fill_price,
            commission=commission,
            slippage_cost=abs(fill_price - self.current_prices.get(event.symbol, 0.0)) * event.quantity,
            side=event.side,
            order_id=event.order_id,
            timestamp=event.timestamp,
        )
        self._emit(fill)

    def _on_fill(self, event: FillEvent):
        self.total_commission += event.commission
        self.total_slippage += event.slippage_cost

        if event.side == "buy":
            self.cash -= event.fill_price * event.quantity + event.commission
            self.position_tracker.open_position(
                event.symbol, event.quantity, event.fill_price, "long"
            )
        else:
            pnl = self.position_tracker.close_position(
                event.symbol, event.quantity, event.fill_price
            )
            self.cash += event.fill_price * event.quantity - event.commission
            self.trades.append({
                "symbol": event.symbol,
                "quantity": event.quantity,
                "entry_price": self.position_tracker._last_entry_price,
                "exit_price": event.fill_price,
                "pnl": pnl - event.commission,
                "commission": event.commission,
                "side": event.side,
                "timestamp": event.timestamp,
                "order_id": event.order_id,
            })

    def run(self) -> BacktestResult:
        """Run the backtest over all data."""
        if not self.data or not self.strategy:
            return BacktestResult(initial_capital=self.initial_capital)

        # Merge all symbols' data into chronological bars
        all_bars: List[Dict[str, Any]] = []
        for symbol, bars in self.data.items():
            for i, bar in enumerate(bars):
                all_bars.append({
                    "symbol": symbol,
                    "index": i,
                    **bar,
                })

        # Sort by timestamp if available, else by index
        if all_bars and "timestamp" in all_bars[0]:
            all_bars.sort(key=lambda b: b["timestamp"])
        else:
            all_bars.sort(key=lambda b: b["index"])

        # Process bars
        for bar in all_bars:
            symbol = bar["symbol"]
            market = MarketEvent(
                symbol=symbol,
                open=bar.get("open", 0.0),
                high=bar.get("high", 0.0),
                low=bar.get("low", 0.0),
                close=bar.get("close", 0.0),
                volume=bar.get("volume", 0.0),
                timestamp=bar.get("timestamp", bar["index"]),
            )
            self.current_prices[symbol] = market.close

            # Strategy generates signals
            context = self._build_context()
            signals = self.strategy.on_market(market, context)
            if signals:
                for sig in signals:
                    self._emit(sig)

            # Process pending orders from OrderManager
            pending_orders = self.order_manager.check_pending(symbol, market)
            for order in pending_orders:
                order_evt = OrderEvent(
                    symbol=order.symbol, quantity=order.quantity,
                    side=order.side.value, order_type=order.order_type.value,
                    price=order.price, order_id=order.order_id,
                    timestamp=market.timestamp,
                )
                self._emit(order_evt)

            self._drain()

            # Mark to market
            equity = self.cash + self.position_tracker.get_portfolio_value(self.current_prices)
            self.equity_curve.append(equity)

        # Build result
        curve = self.equity_curve
        returns = BacktestResult._compute_returns(curve)
        n_bars = len(curve)

        # Monthly returns
        monthly_returns: Dict[str, float] = {}
        if all_bars:
            month_start_equity = curve[0] if curve else self.initial_capital
            current_month = None
            for i, bar in enumerate(all_bars):
                ts = bar.get("timestamp")
                if ts and hasattr(ts, "strftime"):
                    month_key = ts.strftime("%Y-%m")
                    if current_month != month_key:
                        if current_month is not None and month_start_equity > 0:
                            monthly_returns[current_month] = (curve[i - 1] / month_start_equity) - 1
                        current_month = month_key
                        month_start_equity = curve[i] if i < len(curve) else month_start_equity
            if current_month and month_start_equity > 0 and curve:
                monthly_returns[current_month] = (curve[-1] / month_start_equity) - 1

        final_equity = curve[-1] if curve else self.initial_capital

        return BacktestResult(
            total_return=(final_equity / self.initial_capital) - 1 if self.initial_capital > 0 else 0.0,
            cagr=BacktestResult._compute_cagr(self.initial_capital, final_equity, n_bars),
            sharpe=BacktestResult._compute_sharpe(returns),
            sortino=BacktestResult._compute_sortino(returns),
            max_drawdown=BacktestResult._compute_max_drawdown(curve),
            win_rate=BacktestResult._compute_win_rate(self.trades),
            profit_factor=BacktestResult._compute_profit_factor(self.trades),
            trades=self.trades,
            equity_curve=curve,
            monthly_returns=monthly_returns,
            num_trades=len(self.trades),
            final_equity=final_equity,
            initial_capital=self.initial_capital,
            total_commission=self.total_commission,
            total_slippage=self.total_slippage,
        )
