"""Trade-level analytics — win rate, profit factor, time-based breakdowns."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class Trade:
    """A completed trade."""
    entry_time: datetime
    exit_time: datetime
    pnl: float  # profit/loss in currency
    pnl_pct: float  # profit/loss as percentage
    symbol: str = ''
    side: str = 'long'  # 'long' or 'short'


class TradeAnalyzer:
    """Comprehensive trade-level analysis."""

    def __init__(self):
        self._last_analysis = None

    def analyze(self, trades: list) -> dict:
        """Analyze a list of trades and return comprehensive statistics.

        Args:
            trades: list of Trade objects

        Returns:
            dict with trade statistics
        """
        if not trades:
            return self._empty_result()

        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total if total > 0 else 0

        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        # Consecutive wins/losses
        max_consec_wins, max_consec_losses = self._consecutive(pnls)

        # Hold times
        hold_times = [(t.exit_time - t.entry_time) for t in trades]
        avg_hold = sum(hold_times, timedelta()) / len(hold_times) if hold_times else timedelta()

        # Best/worst
        best = max(trades, key=lambda t: t.pnl)
        worst = min(trades, key=lambda t: t.pnl)

        # Time breakdowns
        by_weekday = self._by_weekday(trades)
        by_hour = self._by_hour(trades)
        by_month = self._by_month(trades)

        self._last_analysis = {
            'total_trades': total,
            'win_rate': round(win_rate, 4),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 4) if profit_factor != float('inf') else float('inf'),
            'expectancy': round(expectancy, 2),
            'max_consecutive_wins': max_consec_wins,
            'max_consecutive_losses': max_consec_losses,
            'avg_hold_time': str(avg_hold),
            'best_trade': {'pnl': round(best.pnl, 2), 'symbol': best.symbol, 'time': str(best.entry_time)},
            'worst_trade': {'pnl': round(worst.pnl, 2), 'symbol': worst.symbol, 'time': str(worst.entry_time)},
            'by_weekday': by_weekday,
            'by_hour': by_hour,
            'by_month': by_month,
            'total_pnl': round(sum(pnls), 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
        }
        return self._last_analysis

    def render_html(self, output_path: str) -> None:
        """Render the last analysis as an HTML report.

        Args:
            output_path: file path to write HTML
        """
        if self._last_analysis is None:
            raise RuntimeError("Call analyze() before render_html()")

        a = self._last_analysis
        rows = ''.join(
            f'<tr><td>{k}</td><td>{v}</td></tr>'
            for k, v in a.items()
            if k not in ('by_weekday', 'by_hour', 'by_month', 'best_trade', 'worst_trade')
        )

        weekday_rows = ''.join(
            f'<tr><td>{day}</td><td>{stats["trades"]}</td><td>{stats["pnl"]:.2f}</td></tr>'
            for day, stats in a['by_weekday'].items()
        )

        html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Trade Analysis</title>
<style>
body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }}
table {{ border-collapse: collapse; margin: 10px 0; }}
td, th {{ border: 1px solid #444; padding: 6px 12px; text-align: left; }}
th {{ background: #16213e; }}
h2 {{ color: #e94560; }}
.positive {{ color: #0f0; }} .negative {{ color: #f44; }}
</style></head><body>
<h1>📊 Trade Analysis Report</h1>
<h2>Summary</h2>
<table><tr><th>Metric</th><th>Value</th></tr>{rows}</table>
<h2>Best Trade</h2>
<p class="positive">{a['best_trade']['symbol']} +{a['best_trade']['pnl']:.2f} @ {a['best_trade']['time']}</p>
<h2>Worst Trade</h2>
<p class="negative">{a['worst_trade']['symbol']} {a['worst_trade']['pnl']:.2f} @ {a['worst_trade']['time']}</p>
<h2>By Weekday</h2>
<table><tr><th>Day</th><th>Trades</th><th>PnL</th></tr>{weekday_rows}</table>
</body></html>'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _consecutive(self, pnls: list) -> tuple:
        max_w = max_l = cur_w = cur_l = 0
        for p in pnls:
            if p > 0:
                cur_w += 1
                cur_l = 0
            else:
                cur_l += 1
                cur_w = 0
            max_w = max(max_w, cur_w)
            max_l = max(max_l, cur_l)
        return max_w, max_l

    def _by_weekday(self, trades: list) -> dict:
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        result = {d: {'trades': 0, 'pnl': 0.0} for d in days}
        for t in trades:
            day = days[t.entry_time.weekday()]
            result[day]['trades'] += 1
            result[day]['pnl'] += t.pnl
        # Remove empty days
        return {d: v for d, v in result.items() if v['trades'] > 0}

    def _by_hour(self, trades: list) -> dict:
        result = defaultdict(lambda: {'trades': 0, 'pnl': 0.0})
        for t in trades:
            h = t.entry_time.hour
            result[h]['trades'] += 1
            result[h]['pnl'] += t.pnl
        return dict(sorted(result.items()))

    def _by_month(self, trades: list) -> dict:
        result = defaultdict(lambda: {'trades': 0, 'pnl': 0.0})
        for t in trades:
            key = t.entry_time.strftime('%Y-%m')
            result[key]['trades'] += 1
            result[key]['pnl'] += t.pnl
        return dict(sorted(result.items()))

    def _empty_result(self) -> dict:
        return {
            'total_trades': 0, 'win_rate': 0, 'avg_win': 0, 'avg_loss': 0,
            'profit_factor': 0, 'expectancy': 0,
            'max_consecutive_wins': 0, 'max_consecutive_losses': 0,
            'avg_hold_time': '0:00:00', 'best_trade': None, 'worst_trade': None,
            'by_weekday': {}, 'by_hour': {}, 'by_month': {},
            'total_pnl': 0, 'gross_profit': 0, 'gross_loss': 0,
        }
