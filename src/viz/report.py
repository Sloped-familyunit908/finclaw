"""Backtest report visualizer — terminal-rendered performance reports."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .charts import TerminalChart

_GREEN = "\033[32m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


class BacktestResult:
    """Lightweight stand-in so the module works standalone.

    When used with the real engine, pass engine.BacktestResult directly —
    it has the same attribute names.
    """

    def __init__(self, **kwargs):
        self.total_return: float = kwargs.get("total_return", 0.0)
        self.cagr: float = kwargs.get("cagr", 0.0)
        self.sharpe: float = kwargs.get("sharpe", 0.0)
        self.sortino: float = kwargs.get("sortino", 0.0)
        self.max_drawdown: float = kwargs.get("max_drawdown", 0.0)
        self.win_rate: float = kwargs.get("win_rate", 0.0)
        self.profit_factor: float = kwargs.get("profit_factor", 0.0)
        self.trades: List[Dict[str, Any]] = kwargs.get("trades", [])
        self.equity_curve: List[float] = kwargs.get("equity_curve", [])
        self.monthly_returns: Dict[str, float] = kwargs.get("monthly_returns", {})
        self.num_trades: int = kwargs.get("num_trades", 0)
        self.final_equity: float = kwargs.get("final_equity", 0.0)
        self.initial_capital: float = kwargs.get("initial_capital", 0.0)


class BacktestVisualizer:
    """Generate terminal-based backtest reports."""

    def equity_curve(self, result, width: int = 80, height: int = 15) -> str:
        """Render the equity curve as a braille line chart."""
        curve = getattr(result, "equity_curve", [])
        if not curve:
            return "(no equity data)"
        return TerminalChart.line(curve, width=width, height=height, label="Equity Curve")

    def drawdown_chart(self, result, width: int = 80, height: int = 10) -> str:
        """Render drawdown over time."""
        curve = getattr(result, "equity_curve", [])
        if len(curve) < 2:
            return "(insufficient data)"

        # Compute drawdown series
        peak = curve[0]
        dd_series: list[float] = []
        for v in curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0.0
            dd_series.append(-dd)  # negative for visual

        return TerminalChart.line(dd_series, width=width, height=height, label="Drawdown %")

    def monthly_returns_heatmap(self, result) -> str:
        """Render monthly returns as a heatmap grid (months × years)."""
        monthly = getattr(result, "monthly_returns", {})
        if not monthly:
            return "(no monthly data)"

        # Parse keys like "2024-01" → (year, month)
        parsed: dict[int, dict[int, float]] = {}
        for key, val in monthly.items():
            parts = str(key).split("-")
            if len(parts) == 2:
                y, m = int(parts[0]), int(parts[1])
                parsed.setdefault(y, {})[m] = val

        if not parsed:
            return "(no parseable monthly data)"

        years = sorted(parsed.keys())
        months = list(range(1, 13))
        month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        matrix: list[list[float]] = []
        for y in years:
            row = [parsed.get(y, {}).get(m, 0.0) for m in months]
            matrix.append(row)

        return TerminalChart.heatmap(matrix, month_labels, [str(y) for y in years])

    def trade_scatter(self, result, width: int = 60) -> str:
        """Render trade P/L as a bar chart (most recent trades)."""
        trades = getattr(result, "trades", [])
        if not trades:
            return "(no trades)"

        # Take last 20 trades
        recent = trades[-20:]
        labels = [f"T{i + 1}" for i in range(len(recent))]
        values = []
        for t in recent:
            if isinstance(t, dict):
                values.append(t.get("pnl", t.get("profit", 0.0)))
            else:
                values.append(0.0)

        return TerminalChart.bar(labels, values, width=width)

    def full_report(self, result, width: int = 80) -> str:
        """Render a comprehensive text report with all charts."""
        sections: list[str] = []

        # Header
        sections.append(f"{_BOLD}{'═' * width}{_RESET}")
        sections.append(f"{_BOLD}  BACKTEST REPORT{_RESET}")
        sections.append(f"{_BOLD}{'═' * width}{_RESET}")

        # Key metrics
        tr = getattr(result, "total_return", 0) * 100
        cagr = getattr(result, "cagr", 0) * 100
        sharpe = getattr(result, "sharpe", 0)
        sortino = getattr(result, "sortino", 0)
        mdd = getattr(result, "max_drawdown", 0) * 100
        wr = getattr(result, "win_rate", 0) * 100
        pf = getattr(result, "profit_factor", 0)
        nt = getattr(result, "num_trades", 0)

        c_tr = _GREEN if tr >= 0 else _RED
        sections.append(
            f"  Return: {c_tr}{tr:+.2f}%{_RESET}  |  CAGR: {cagr:.2f}%  |  "
            f"Sharpe: {sharpe:.2f}  |  Sortino: {sortino:.2f}"
        )
        sections.append(
            f"  Max DD: {_RED}{mdd:.2f}%{_RESET}  |  Win Rate: {wr:.1f}%  |  "
            f"Profit Factor: {pf:.2f}  |  Trades: {nt}"
        )
        sections.append("")

        # Charts
        sections.append(self.equity_curve(result, width=width))
        sections.append("")
        sections.append(self.drawdown_chart(result, width=width))
        sections.append("")

        hm = self.monthly_returns_heatmap(result)
        if "(no" not in hm:
            sections.append(f"{_BOLD}Monthly Returns Heatmap{_RESET}")
            sections.append(hm)
            sections.append("")

        ts = self.trade_scatter(result, width=width)
        if "(no" not in ts:
            sections.append(f"{_BOLD}Trade P/L{_RESET}")
            sections.append(ts)

        sections.append(f"{_BOLD}{'═' * width}{_RESET}")
        return "\n".join(sections)
