"""FinClaw Enhanced Backtesting Engine v2.9.0"""
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
]
