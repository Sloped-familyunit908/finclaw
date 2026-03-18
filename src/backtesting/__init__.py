"""FinClaw Enhanced Backtesting Engine v3.6.0

Extended backtesting analysis tools: walk-forward optimization, realistic simulation,
benchmarks, strategy comparison, overfit detection, and survivorship bias checking.

Module distinction:
  - `src.backtest` → Core backtest engine (BacktestEngine, OrderManager, etc.)
  - `src.backtesting` (this module) → Extended analysis tools (walk-forward, realistic
    simulation, benchmarks, strategy comparison, overfit detection, survivorship bias)

Both modules are canonical — they serve complementary purposes.
"""
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
