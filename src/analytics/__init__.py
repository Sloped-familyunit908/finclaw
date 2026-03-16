"""FinClaw Performance Analytics v3.2.0"""
from .metrics import PerformanceMetrics
from .rolling import RollingAnalysis
from .regime import RegimeAnalyzer
from .tca import TCA, TCAReport, TradeFill
from .sensitivity import SensitivityAnalyzer, SensitivityResult
from .drawdown import DrawdownAnalyzer, DrawdownPeriod
from .trade_analyzer import TradeAnalyzer, Trade
from .liquidity import LiquidityAnalyzer, LiquidityData
from .tax_calculator import TaxCalculator, TaxLot
from .benchmark import BenchmarkComparator

__all__ = [
    "PerformanceMetrics", "RollingAnalysis", "RegimeAnalyzer",
    "TCA", "TCAReport", "TradeFill",
    "SensitivityAnalyzer", "SensitivityResult",
    "DrawdownAnalyzer", "DrawdownPeriod",
    "TradeAnalyzer", "Trade",
    "LiquidityAnalyzer", "LiquidityData",
    "TaxCalculator", "TaxLot",
    "BenchmarkComparator",
]
