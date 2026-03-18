"""FinClaw Backtesting Module v4.0.0

The canonical backtesting module. Contains both the core backtest engine
(BacktestEngine, OrderManager, PositionTracker) and extended analysis tools
(walk-forward, realistic simulation, benchmarks, strategy comparison,
overfit detection, survivorship bias checking).

Note: ``src.backtest`` is deprecated and re-exports from this module.
"""
# --- Core engine (moved from src.backtest) ---
from .core_engine import (
    BacktestEngine,
    BacktestResult as CoreBacktestResult,
    EventType as CoreEventType,
    Event as CoreEvent,
    MarketEvent as CoreMarketEvent,
    SignalEvent as CoreSignalEvent,
    OrderEvent as CoreOrderEvent,
    FillEvent as CoreFillEvent,
    Strategy as StrategyProtocol,
    StrategyContext,
)
from .orders import OrderManager, Order, OrderType as CoreOrderType, OrderSide as CoreOrderSide, OrderStatus
from .positions import PositionTracker, Position, PositionSide
from .core_monte_carlo import MonteCarloSimulator as CoreMonteCarloSimulator, MonteCarloResult

# --- Extended analysis tools ---
from .walk_forward import WalkForwardAnalyzer
from .walk_forward_v2 import WalkForwardOptimizer, WalkForwardResult, WindowResult
from .monte_carlo import MonteCarloSimulator
from .multi_timeframe import MultiTimeframeBacktester
from .benchmark import BenchmarkComparison
from .realistic import (
    RealisticBacktester, BacktestConfig, BacktestResult as RealisticResult,
    SlippageModel, CommissionModel, MarketImpactModel, SimpleOrderBook,
    OrderType, OrderSide, FillStatus,
)
from .benchmarks import (
    BuyAndHold, EqualWeight, ClassicPortfolio, RiskParityBenchmark,
    BenchmarkResult, BENCHMARKS, run_all_benchmarks,
)
from .compare import StrategyComparator, ComparisonResult, StrategyMetrics
from .overfit_check import OverfitDetector
from .survivorship import SurvivorshipBiasChecker, SurvivorshipReport
from .event_engine import (
    EventDrivenBacktester, EventType, Event,
    MarketEvent, SignalEvent, OrderEvent, FillEvent,
    Portfolio, BacktestResult as EventBacktestResult,
)
from .slippage import SlippageModel as SlippageModelV2
from .commission import CommissionModel as CommissionModelV2

__all__ = [
    # Core engine (from src.backtest)
    "BacktestEngine", "CoreBacktestResult",
    "CoreEventType", "CoreEvent", "CoreMarketEvent", "CoreSignalEvent",
    "CoreOrderEvent", "CoreFillEvent",
    "StrategyProtocol", "StrategyContext",
    "OrderManager", "Order", "CoreOrderType", "CoreOrderSide", "OrderStatus",
    "PositionTracker", "Position", "PositionSide",
    "CoreMonteCarloSimulator", "MonteCarloResult",
    # Extended analysis
    "WalkForwardAnalyzer",
    "WalkForwardOptimizer", "WalkForwardResult", "WindowResult",
    "MonteCarloSimulator",
    "MultiTimeframeBacktester",
    "BenchmarkComparison",
    "RealisticBacktester", "BacktestConfig", "RealisticResult",
    "SlippageModel", "CommissionModel", "MarketImpactModel", "SimpleOrderBook",
    "OrderType", "OrderSide", "FillStatus",
    "BuyAndHold", "EqualWeight", "ClassicPortfolio", "RiskParityBenchmark",
    "BenchmarkResult", "BENCHMARKS", "run_all_benchmarks",
    "StrategyComparator", "ComparisonResult", "StrategyMetrics",
    "OverfitDetector", "SurvivorshipBiasChecker", "SurvivorshipReport",
    "EventDrivenBacktester", "EventType", "Event",
    "MarketEvent", "SignalEvent", "OrderEvent", "FillEvent",
    "Portfolio", "EventBacktestResult",
    "SlippageModelV2", "CommissionModelV2",
]
