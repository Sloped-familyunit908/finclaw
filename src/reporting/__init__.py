"""
DEPRECATED: Use ``src.reports`` for report generation.

This module (``src.reporting``) is deprecated and will be removed in v6.0.
The canonical reporting module is ``src.reports``, which now contains
tearsheets, comparisons, and all report generators.

All exports are re-exported here for backward compatibility.
"""

import warnings as _warnings

_warnings.warn(
    "src.reporting is deprecated. Use src.reports for report generation. "
    "This module will be removed in v6.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
from .html_report import BacktestReportGenerator, BacktestResult
from .tearsheet import Tearsheet
from .comparison import StrategyComparison

__all__ = [
    "BacktestReportGenerator",
    "BacktestResult",
    "Tearsheet",
    "StrategyComparison",
]
