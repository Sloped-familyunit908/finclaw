"""Portfolio dashboard — rich terminal rendering."""

from __future__ import annotations

from typing import Any, Dict, List

from .charts import TerminalChart

_GREEN = "\033[32m"
_RED = "\033[31m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _pnl_color(val: float) -> str:
    return _GREEN if val >= 0 else _RED


def _pct_str(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.1f}%"


def _money(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}${val:,.0f}"


class PortfolioDashboard:
    """Render a box-drawn portfolio dashboard in the terminal.

    Expected *portfolio* dict shape::

        {
            "total_value": 125430.0,
            "total_cost": 120000.0,
            "holdings": [
                {"symbol": "AAPL", "weight": 0.45, "pnl_pct": 2.3,
                 "value": 56443, "cost": 55000},
                ...
            ],
            "history": [120000, 121000, ...],  # daily equity values
        }
    """

    def render(self, portfolio: dict, width: int = 50) -> str:
        total = portfolio.get("total_value", 0)
        cost = portfolio.get("total_cost", 0)
        pnl = total - cost
        pnl_pct = (pnl / cost * 100) if cost else 0
        holdings = portfolio.get("holdings", [])
        history = portfolio.get("history", [])

        iw = width - 4  # inner width

        lines: list[str] = []
        # Top
        lines.append(f"┌─ Portfolio {'─' * (iw - 12)}┐")
        # Summary
        summary = f"Total: ${total:,.0f}  P/L: {_pnl_color(pnl)}{_money(pnl)} ({_pct_str(pnl_pct)}){_RESET}"
        lines.append(f"│ {summary:<{iw + _ansi_pad(summary)}} │")
        # Holdings header
        lines.append(f"├─ Holdings {'─' * (iw - 11)}┤")
        for h in holdings:
            sym = h.get("symbol", "???")
            w = h.get("weight", 0)
            pnl_h = h.get("pnl_pct", 0)
            bar_len = int(w * 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            color = _pnl_color(pnl_h)
            entry = f"{sym:<6} {w * 100:>4.0f}%  {bar}  {color}{_pct_str(pnl_h)}{_RESET}"
            lines.append(f"│ {entry:<{iw + _ansi_pad(entry)}} │")
        # Sparkline
        if history:
            lines.append(f"├─ 7d Performance {'─' * (iw - 17)}┤")
            spark = TerminalChart.sparkline(history[-7:] if len(history) >= 7 else history)
            lines.append(f"│ {spark:<{iw}} │")
        # Bottom
        lines.append(f"└{'─' * (iw + 2)}┘")
        return "\n".join(lines)


def _ansi_pad(s: str) -> int:
    """Return extra chars from ANSI escape sequences for padding."""
    import re
    ansi_len = len(re.sub(r"\033\[[0-9;]*m", "", s))
    return len(s) - ansi_len
