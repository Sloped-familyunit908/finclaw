"""Performance Report Generator — comprehensive HTML backtest reports with SVG charts."""

from __future__ import annotations

import html
import math
from datetime import datetime
from typing import Any


class PerformanceReport:
    """Generate comprehensive HTML backtest reports with embedded SVG charts."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, result: dict, benchmark: dict | None = None) -> str:
        """Return a full HTML page with equity curve, drawdown, monthly heatmap,
        rolling Sharpe, key metrics table, and trade list."""
        equity = result.get("equity", [])
        returns = result.get("returns", [])
        trades = result.get("trades", [])
        metrics = result.get("metrics", {})
        dates = result.get("dates", [])

        if not equity:
            return "<html><body><h1>No equity data</h1></body></html>"

        if not returns and len(equity) > 1:
            returns = [(equity[i] / equity[i - 1]) - 1.0 for i in range(1, len(equity))]

        monthly = self.generate_monthly_returns(equity, dates)
        rolling = self.generate_rolling_metrics(returns)

        bench_equity = benchmark.get("equity", []) if benchmark else []
        bench_label = benchmark.get("label", "Benchmark") if benchmark else "Benchmark"

        parts = [
            self._html_head(metrics.get("strategy_name", "Backtest Report")),
            '<body><div class="container">',
            self._metrics_table(metrics),
            self._equity_svg(equity, bench_equity, dates, bench_label),
            self._drawdown_svg(equity, dates),
            self._monthly_heatmap(monthly),
            self._rolling_sharpe_svg(rolling.get("rolling_sharpe", []), dates),
            self._trade_table(trades),
            "</div></body></html>",
        ]
        return "\n".join(parts)

    # ------------------------------------------------------------------
    def generate_monthly_returns(self, equity: list[float], dates: list[str] | None = None) -> dict:
        """Monthly returns matrix {year: {month: return}}."""
        if len(equity) < 2:
            return {}

        if dates and len(dates) == len(equity):
            parsed = [self._parse_date(d) for d in dates]
        else:
            # Assume daily from today backwards
            base = datetime.now()
            parsed = [datetime(base.year, base.month, base.day)] * len(equity)

        result: dict[int, dict[int, float]] = {}
        month_start_val = equity[0]
        prev_year, prev_month = parsed[0].year, parsed[0].month

        for i in range(1, len(equity)):
            y, m = parsed[i].year, parsed[i].month
            if y != prev_year or m != prev_month:
                # Close previous month
                ret = (equity[i - 1] / month_start_val - 1.0) if month_start_val > 0 else 0.0
                result.setdefault(prev_year, {})[prev_month] = ret
                month_start_val = equity[i - 1]
                prev_year, prev_month = y, m

        # Last partial month
        if month_start_val > 0:
            ret = (equity[-1] / month_start_val - 1.0)
            result.setdefault(prev_year, {})[prev_month] = ret

        return result

    def generate_rolling_metrics(self, returns: list[float], window: int = 63) -> dict:
        """Rolling Sharpe and volatility over *window* periods."""
        n = len(returns)
        rolling_sharpe: list[float] = []
        rolling_vol: list[float] = []

        for i in range(n):
            if i < window - 1:
                rolling_sharpe.append(float("nan"))
                rolling_vol.append(float("nan"))
                continue
            chunk = returns[i - window + 1: i + 1]
            mean_r = sum(chunk) / window
            var_r = sum((r - mean_r) ** 2 for r in chunk) / (window - 1)
            std_r = math.sqrt(var_r) if var_r > 0 else 0.0
            rolling_vol.append(std_r * math.sqrt(252))
            rolling_sharpe.append((mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0.0)

        return {"rolling_sharpe": rolling_sharpe, "rolling_volatility": rolling_vol}

    # ------------------------------------------------------------------
    # Private helpers — HTML generation
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(d: Any) -> datetime:
        if isinstance(d, datetime):
            return d
        if isinstance(d, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    return datetime.strptime(d, fmt)
                except ValueError:
                    continue
        return datetime(2000, 1, 1)

    @staticmethod
    def _html_head(title: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{html.escape(title)}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       margin: 0; padding: 20px; background: #fafafa; color: #333; }}
.container {{ max-width: 1100px; margin: 0 auto; }}
h2 {{ margin-top: 32px; border-bottom: 2px solid #2196F3; padding-bottom: 6px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: right; }}
th {{ background: #2196F3; color: #fff; }}
tr:nth-child(even) {{ background: #f5f5f5; }}
.metric-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }}
.metric-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 14px; }}
.metric-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
.metric-card .value {{ font-size: 22px; font-weight: 600; margin-top: 4px; }}
.positive {{ color: #4CAF50; }} .negative {{ color: #F44336; }}
svg {{ width: 100%; height: auto; }}
.heatmap td {{ width: 60px; text-align: center; font-size: 12px; }}
</style></head>"""

    def _metrics_table(self, metrics: dict) -> str:
        if not metrics:
            return ""
        cards = ['<h2>Key Metrics</h2><div class="metric-grid">']
        for key, val in metrics.items():
            css = ""
            display = val
            if isinstance(val, float):
                if "return" in key.lower() or "pnl" in key.lower():
                    css = "positive" if val >= 0 else "negative"
                    display = f"{val:+.2%}"
                elif "ratio" in key.lower() or "sharpe" in key.lower():
                    css = "positive" if val >= 0 else "negative"
                    display = f"{val:.3f}"
                elif "drawdown" in key.lower():
                    css = "negative" if val > 0 else ""
                    display = f"{val:.2%}"
                else:
                    display = f"{val:,.2f}"
            label = key.replace("_", " ").title()
            cards.append(f'<div class="metric-card"><div class="label">{html.escape(label)}</div>'
                         f'<div class="value {css}">{html.escape(str(display))}</div></div>')
        cards.append("</div>")
        return "\n".join(cards)

    # ------------------------------------------------------------------
    # SVG chart helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _polyline(values: list[float], width: int, height: int, pad: int = 40) -> str:
        if not values:
            return ""
        n = len(values)
        mn, mx = min(values), max(values)
        rng = mx - mn if mx != mn else 1.0
        points = []
        for i, v in enumerate(values):
            x = pad + i / max(n - 1, 1) * (width - 2 * pad)
            y = pad + (1 - (v - mn) / rng) * (height - 2 * pad)
            points.append(f"{x:.1f},{y:.1f}")
        return " ".join(points)

    def _equity_svg(self, equity: list[float], bench: list[float],
                    dates: list[str] | None, bench_label: str) -> str:
        w, h = 1000, 350
        svg = [f'<h2>Equity Curve</h2><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
        svg.append(f'<rect width="{w}" height="{h}" fill="#fff" rx="8"/>')
        pts = self._polyline(equity, w, h)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#2196F3" stroke-width="2"/>')
        if bench:
            bpts = self._polyline(bench, w, h)
            svg.append(f'<polyline points="{bpts}" fill="none" stroke="#FF9800" stroke-width="1.5" stroke-dasharray="5,3"/>')
            svg.append(f'<text x="{w - 120}" y="25" font-size="12" fill="#FF9800">{html.escape(bench_label)}</text>')
        svg.append(f'<text x="{w - 120}" y="45" font-size="12" fill="#2196F3">Strategy</text>')
        svg.append("</svg>")
        return "\n".join(svg)

    def _drawdown_svg(self, equity: list[float], dates: list[str] | None) -> str:
        if len(equity) < 2:
            return ""
        dd = []
        peak = equity[0]
        for v in equity:
            if v > peak:
                peak = v
            dd.append((v - peak) / peak if peak > 0 else 0.0)

        w, h = 1000, 200
        svg = [f'<h2>Drawdown</h2><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
        svg.append(f'<rect width="{w}" height="{h}" fill="#fff" rx="8"/>')
        pts = self._polyline(dd, w, h)
        # Fill area
        pad = 40
        first_x = pad
        last_x = pad + (len(dd) - 1) / max(len(dd) - 1, 1) * (w - 2 * pad)
        zero_y = pad  # top = max = 0
        svg.append(f'<polyline points="{first_x},{zero_y} {pts} {last_x:.1f},{zero_y}" '
                    f'fill="rgba(244,67,54,0.2)" stroke="#F44336" stroke-width="1.5"/>')
        svg.append("</svg>")
        return "\n".join(svg)

    def _monthly_heatmap(self, monthly: dict) -> str:
        if not monthly:
            return ""
        rows = ['<h2>Monthly Returns</h2><table class="heatmap"><tr><th>Year</th>']
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for m in months:
            rows.append(f"<th>{m}</th>")
        rows.append("<th>Annual</th></tr>")

        for year in sorted(monthly):
            row = [f"<tr><td><b>{year}</b></td>"]
            annual = 1.0
            for m in range(1, 13):
                val = monthly[year].get(m)
                if val is not None:
                    annual *= (1 + val)
                    color = f"rgba(76,175,80,{min(abs(val) * 5, 0.8):.2f})" if val >= 0 else f"rgba(244,67,54,{min(abs(val) * 5, 0.8):.2f})"
                    row.append(f'<td style="background:{color}">{val:+.1%}</td>')
                else:
                    row.append("<td>—</td>")
            annual_ret = annual - 1.0
            color = "positive" if annual_ret >= 0 else "negative"
            row.append(f'<td class="{color}"><b>{annual_ret:+.1%}</b></td></tr>')
            rows.append("".join(row))
        rows.append("</table>")
        return "\n".join(rows)

    def _rolling_sharpe_svg(self, sharpe: list[float], dates: list[str] | None) -> str:
        clean = [v for v in sharpe if not (isinstance(v, float) and math.isnan(v))]
        if len(clean) < 10:
            return ""
        w, h = 1000, 250
        svg = [f'<h2>Rolling Sharpe (63-day)</h2><svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
        svg.append(f'<rect width="{w}" height="{h}" fill="#fff" rx="8"/>')
        pts = self._polyline(clean, w, h)
        svg.append(f'<polyline points="{pts}" fill="none" stroke="#9C27B0" stroke-width="1.5"/>')
        # Zero line
        mn, mx = min(clean), max(clean)
        rng = mx - mn if mx != mn else 1.0
        zero_y = 40 + (1 - (0 - mn) / rng) * (h - 80)
        if 40 <= zero_y <= h - 40:
            svg.append(f'<line x1="40" y1="{zero_y:.1f}" x2="{w - 40}" y2="{zero_y:.1f}" stroke="#999" stroke-dasharray="4,4"/>')
        svg.append("</svg>")
        return "\n".join(svg)

    @staticmethod
    def _trade_table(trades: list[dict]) -> str:
        if not trades:
            return ""
        rows = ['<h2>Trade List</h2><table><tr>']
        cols = ["#", "Date", "Ticker", "Side", "Shares", "Price", "PnL"]
        for c in cols:
            rows.append(f"<th>{c}</th>")
        rows.append("</tr>")
        for i, t in enumerate(trades[:200], 1):
            pnl = t.get("pnl", 0)
            css = "positive" if pnl >= 0 else "negative"
            rows.append(f'<tr><td>{i}</td><td>{t.get("date", "")}</td>'
                        f'<td>{t.get("ticker", "")}</td><td>{t.get("side", "")}</td>'
                        f'<td>{t.get("shares", "")}</td><td>{t.get("price", "")}</td>'
                        f'<td class="{css}">{pnl:+.2f}</td></tr>')
        rows.append("</table>")
        return "\n".join(rows)
