"""FinClaw Enhanced Backtest Engine v5.6.0

Core event-driven backtesting engine with order management, position tracking,
and Monte Carlo simulation.

Module distinction:
  - `src.backtest` (this module) → Core backtest engine (BacktestEngine, OrderManager, etc.)
  - `src.backtesting` → Extended analysis tools (walk-forward, realistic simulation,
    benchmarks, strategy comparison, overfit detection, survivorship bias checking)

Both modules are canonical — they serve complementary purposes.
"""

from .engine import (
    BacktestEngine,
    BacktestResult,
    EventType,
    Event,
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)
from .orders import OrderManager, Order, OrderType, OrderSide, OrderStatus
from .positions import PositionTracker, Position, PositionSide
from .monte_carlo import MonteCarloSimulator, MonteCarloResult

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "EventType",
    "Event",
    "MarketEvent",
    "SignalEvent",
    "OrderEvent",
    "FillEvent",
    "OrderManager",
    "Order",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "PositionTracker",
    "Position",
    "PositionSide",
    "MonteCarloSimulator",
    "MonteCarloResult",
]
