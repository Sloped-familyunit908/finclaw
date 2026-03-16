"""
Paper Trading Dashboard - terminal-based portfolio display.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.paper.engine import PaperTradingEngine


def _sparkline(values: list[float], width: int = 20) -> str:
    """Generate a sparkline from numeric values."""
    if not values:
        return ""
    blocks = " ▁▂▃▄▅▆▇█"
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    # Sample to width
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
    return "".join(blocks[min(8, int((v - mn) / rng * 8))] for v in sampled)


class PaperDashboard:
    """Render a text-based paper trading dashboard."""

    def render(self, engine: "PaperTradingEngine") -> str:
        portfolio = engine.get_portfolio()
        pnl = engine.get_pnl()
        trades = engine.get_trade_history()

        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("  📄 PAPER TRADING DASHBOARD")
        lines.append("=" * 60)
        lines.append("")

        # Balance
        lines.append(f"  💰 Cash:           ${portfolio.cash:>12,.2f}")
        lines.append(f"  📊 Positions:      ${portfolio.positions_value:>12,.2f}")
        lines.append(f"  💼 Total Value:    ${portfolio.total_value:>12,.2f}")
        lines.append(f"  📈 Total Return:   {portfolio.total_return:>+11.2f}%")
        lines.append("")

        # P&L
        pnl_sign = "+" if pnl.total >= 0 else ""
        lines.append(f"  ── P&L ──")
        lines.append(f"  Realized:    ${pnl.realized:>+12,.2f}")
        lines.append(f"  Unrealized:  ${pnl.unrealized:>+12,.2f}")
        lines.append(f"  Total:       ${pnl_sign}{pnl.total:>11,.2f}")
        if pnl.total_trades > 0:
            lines.append(f"  Win Rate:    {pnl.win_rate:.1f}% ({pnl.win_count}W/{pnl.loss_count}L)")
        lines.append("")

        # Positions
        if portfolio.positions:
            lines.append(f"  ── Positions ({len(portfolio.positions)}) ──")
            lines.append(f"  {'Symbol':<8} {'Qty':>8} {'Avg Cost':>10} {'Price':>10} {'P&L':>12}")
            lines.append(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*12}")
            for sym, pos in sorted(portfolio.positions.items()):
                pnl_val = pos.unrealized_pnl
                lines.append(
                    f"  {sym:<8} {pos.quantity:>8.1f} ${pos.avg_cost:>9.2f} ${pos.current_price:>9.2f} ${pnl_val:>+11.2f}"
                )
            lines.append("")

        # Recent trades
        recent = trades[-5:]
        if recent:
            lines.append(f"  ── Recent Trades ──")
            for t in reversed(recent):
                ts = datetime.fromtimestamp(t["timestamp"]).strftime("%H:%M:%S")
                side = t["side"]
                arrow = "🟢" if side == "BUY" else "🔴"
                lines.append(f"  {arrow} {ts} {side:<4} {t['symbol']:<6} x{t['quantity']:<6} @${t['price']:.2f}")
            lines.append("")

        # Equity sparkline
        equity_data = engine.get_equity_history()
        if equity_data:
            values = [v for _, v in equity_data]
            spark = _sparkline(values)
            lines.append(f"  ── Equity Curve ──")
            lines.append(f"  {spark}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
