"""FinClaw Reports Module v4.0.0

The canonical reporting module. Contains report generators for backtests,
performance analysis, PDF output, tearsheets, and strategy comparisons.

Note: ``src.reporting`` is deprecated and re-exports from this module.
"""
from .backtest_report import BacktestReportGenerator, BacktestReport
from .pdf_report import PDFReportGenerator
from .report_card import ReportCard, BacktestResult as ReportCardResult
from .performance_report import PerformanceReport
from .tearsheet import Tearsheet
from .comparison import StrategyComparison
from .reporting_html import (
    BacktestReportGenerator as LegacyReportGenerator,
    BacktestResult as LegacyBacktestResult,
)

__all__ = [
    "BacktestReportGenerator", "BacktestReport",
    "PDFReportGenerator",
    "ReportCard", "ReportCardResult",
    "PerformanceReport",
    "Tearsheet",
    "StrategyComparison",
    "LegacyReportGenerator", "LegacyBacktestResult",
]
