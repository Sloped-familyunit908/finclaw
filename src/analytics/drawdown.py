"""Drawdown analysis — max drawdown, periods, pain/ulcer indices, Calmar ratio."""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class DrawdownPeriod:
    """A single drawdown episode."""
    start: int
    end: int
    depth: float  # max drawdown depth (negative)
    duration: int  # periods from start to trough
    recovery_time: Optional[int]  # periods from trough to recovery, None if not recovered


class DrawdownAnalyzer:
    """Analyze drawdowns from an equity curve."""

    def max_drawdown(self, equity_curve: list) -> dict:
        """Calculate maximum drawdown.

        Args:
            equity_curve: list of portfolio values over time

        Returns:
            dict with 'max_dd' (negative float), 'peak_idx', 'trough_idx', 'peak_value', 'trough_value'
        """
        if len(equity_curve) < 2:
            return {'max_dd': 0.0, 'peak_idx': 0, 'trough_idx': 0,
                    'peak_value': equity_curve[0] if equity_curve else 0,
                    'trough_value': equity_curve[0] if equity_curve else 0}

        peak = equity_curve[0]
        peak_idx = 0
        max_dd = 0.0
        max_dd_peak_idx = 0
        max_dd_trough_idx = 0

        for i, val in enumerate(equity_curve):
            if val > peak:
                peak = val
                peak_idx = i
            dd = (val - peak) / peak if peak != 0 else 0
            if dd < max_dd:
                max_dd = dd
                max_dd_peak_idx = peak_idx
                max_dd_trough_idx = i

        return {
            'max_dd': round(max_dd, 6),
            'peak_idx': max_dd_peak_idx,
            'trough_idx': max_dd_trough_idx,
            'peak_value': equity_curve[max_dd_peak_idx],
            'trough_value': equity_curve[max_dd_trough_idx],
        }

    def drawdown_periods(self, equity_curve: list) -> list:
        """Identify all drawdown periods.

        Returns:
            List of DrawdownPeriod with start, end, depth, duration, recovery_time
        """
        if len(equity_curve) < 2:
            return []

        peak = equity_curve[0]
        peak_idx = 0
        periods = []
        in_dd = False
        dd_start = 0
        dd_trough = 0
        dd_trough_idx = 0

        for i, val in enumerate(equity_curve):
            if val >= peak:
                if in_dd:
                    # Recovered
                    recovery = i - dd_trough_idx
                    periods.append(DrawdownPeriod(
                        start=dd_start,
                        end=i,
                        depth=round(dd_trough, 6),
                        duration=dd_trough_idx - dd_start,
                        recovery_time=recovery,
                    ))
                    in_dd = False
                peak = val
                peak_idx = i
            else:
                dd = (val - peak) / peak if peak != 0 else 0
                if not in_dd:
                    in_dd = True
                    dd_start = peak_idx
                    dd_trough = dd
                    dd_trough_idx = i
                elif dd < dd_trough:
                    dd_trough = dd
                    dd_trough_idx = i

        # If still in drawdown at end
        if in_dd:
            periods.append(DrawdownPeriod(
                start=dd_start,
                end=len(equity_curve) - 1,
                depth=round(dd_trough, 6),
                duration=dd_trough_idx - dd_start,
                recovery_time=None,
            ))

        return periods

    def underwater_chart(self, equity_curve: list) -> str:
        """Generate HTML underwater (drawdown) chart.

        Returns:
            HTML string with inline SVG chart
        """
        if len(equity_curve) < 2:
            return '<div>Insufficient data for underwater chart</div>'

        # Calculate drawdown series
        dd_series = []
        peak = equity_curve[0]
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (val - peak) / peak * 100 if peak != 0 else 0
            dd_series.append(dd)

        width = 800
        height = 300
        margin = 40
        plot_w = width - 2 * margin
        plot_h = height - 2 * margin

        min_dd = min(dd_series) if dd_series else 0
        if min_dd >= 0:
            min_dd = -1  # avoid div by zero

        n = len(dd_series)
        points = []
        for i, dd in enumerate(dd_series):
            x = margin + (i / max(n - 1, 1)) * plot_w
            y = margin + (dd / min_dd) * plot_h
            points.append(f"{x:.1f},{y:.1f}")

        # Build SVG path (fill area)
        poly_points = [f"{margin:.1f},{margin:.1f}"] + points + [f"{margin + plot_w:.1f},{margin:.1f}"]

        svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" fill="#1a1a2e"/>
  <polygon points="{' '.join(poly_points)}" fill="rgba(220,50,50,0.4)" stroke="none"/>
  <polyline points="{' '.join(points)}" fill="none" stroke="#dc3232" stroke-width="1.5"/>
  <line x1="{margin}" y1="{margin}" x2="{margin + plot_w}" y2="{margin}" stroke="#555" stroke-width="0.5"/>
  <text x="{margin - 5}" y="{margin + 4}" fill="#aaa" font-size="10" text-anchor="end">0%</text>
  <text x="{margin - 5}" y="{margin + plot_h + 4}" fill="#aaa" font-size="10" text-anchor="end">{min_dd:.1f}%</text>
  <text x="{width / 2}" y="{height - 5}" fill="#aaa" font-size="12" text-anchor="middle">Underwater Chart</text>
</svg>'''

        return f'<div style="font-family:monospace">{svg}</div>'

    def pain_index(self, equity_curve: list) -> float:
        """Calculate Pain Index (average drawdown depth).

        Returns:
            Mean of absolute drawdown values (positive number)
        """
        if len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        total_dd = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak if peak != 0 else 0
            total_dd += dd

        return round(total_dd / len(equity_curve), 6)

    def ulcer_index(self, equity_curve: list) -> float:
        """Calculate Ulcer Index (RMS of drawdowns).

        Returns:
            Root mean square of percentage drawdowns
        """
        if len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        sq_sum = 0.0
        for val in equity_curve:
            if val > peak:
                peak = val
            dd_pct = ((val - peak) / peak * 100) if peak != 0 else 0
            sq_sum += dd_pct ** 2

        return round(math.sqrt(sq_sum / len(equity_curve)), 6)

    def calmar_ratio(self, returns: list, max_dd: float) -> float:
        """Calculate Calmar Ratio (annualized return / max drawdown).

        Args:
            returns: list of periodic returns (e.g., daily)
            max_dd: maximum drawdown as negative float (e.g., -0.20)

        Returns:
            Calmar ratio (positive is good)
        """
        if not returns or max_dd == 0:
            return 0.0

        # Annualize assuming 252 trading days
        total_return = 1.0
        for r in returns:
            total_return *= (1 + r)

        n = len(returns)
        ann_return = total_return ** (252 / n) - 1 if n > 0 else 0

        return round(ann_return / abs(max_dd), 6)
