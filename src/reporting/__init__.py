"""
DEPRECATED: Use `src.reports` for report generation.

This module (`src.reporting`) is deprecated. The canonical reporting module
is `src.reports`, which contains more comprehensive report generators
(backtest reports, PDF, performance reports, report cards).

This module's tearsheet and comparison functionality remain available here
for backward compatibility, but new code should import from `src.reports`.

All exports are re-exported for backward compatibility.
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
