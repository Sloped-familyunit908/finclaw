"""FinClaw Reporting v4.9.0 — Standalone HTML backtest reports, tearsheets, and strategy comparison."""

from .html_report import BacktestReportGenerator, BacktestResult
from .tearsheet import Tearsheet
from .comparison import StrategyComparison

__all__ = [
    "BacktestReportGenerator",
    "BacktestResult",
    "Tearsheet",
    "StrategyComparison",
]
