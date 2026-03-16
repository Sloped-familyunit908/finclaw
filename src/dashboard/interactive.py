"""Interactive HTML Dashboard Generator — standalone, no external dependencies.

Renders inline SVG charts (line, bar, candlestick, heatmap) plus metric cards
and tables into a single self-contained HTML file.
"""

from __future__ import annotations

import html
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional


@dataclass
class _ChartSpec:
    chart_type: str
    data: dict
    title: str


@dataclass
class _TableSpec:
    headers: list
    rows: list
    title: str


@dataclass
class _MetricSpec:
    name: str
    value: float
    change: Optional[float] = None


class InteractiveDashboard:
    """Build a standalone HTML dashboard with inline SVG charts."""

    def __init__(self, title: str = "FinClaw Dashboard"):
        self.title = title
        self._charts: List[_ChartSpec] = []
        self._tables: List[_TableSpec] = []
        self._metrics: List[_MetricSpec] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_chart(self, chart_type: str, data: dict, title: str) -> None:
        """Add a chart. *chart_type*: line | bar | candlestick | heatmap."""
        if chart_type not in ("line", "bar", "candlestick", "heatmap"):
            raise ValueError(f"Unsupported chart type: {chart_type}")
        self._charts.append(_ChartSpec(chart_type, data, title))

    def add_table(self, headers: list, rows: list, title: str) -> None:
        self._tables.append(_TableSpec(headers, rows, title))

    def add_metric(self, name: str, value: float, change: float = None) -> None:
        self._metrics.append(_MetricSpec(name, value, change))

    def render(self, output_path: str) -> str:
        """Write the dashboard to *output_path* and return the HTML string."""
        parts = [self._html_head()]
        if self._metrics:
            parts.append(self._render_metrics())
        for ch in self._charts:
            parts.append(self._render_chart(ch))
        for tb in self._tables:
            parts.append(self._render_table(tb))
        parts.append(self._html_tail())
        content = "\n".join(parts)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
        return content

    # ------------------------------------------------------------------
    # SVG helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scale(values, lo, hi, target_lo, target_hi):
        if lo == hi:
            return [target_lo] * len(values)
        return [target_lo + (v - lo) / (hi - lo) * (target_hi - target_lo) for v in values]

    def _svg_line(self, data: dict, w: int = 700, h: int = 320) -> str:
        labels = data.get("labels", list(range(len(data.get("values", [])))))
        values = data.get("values", [])
        if not values:
            return "<p>No data</p>"
        pad = 60
        mn, mx = min(values), max(values)
        margin = (mx - mn) * 0.05 or 1
        mn -= margin; mx += margin
        ys = self._scale(values, mn, mx, h - pad, pad)
        xs = self._scale(list(range(len(values))), 0, max(1, len(values) - 1), pad, w - pad)
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{w}px">']
        # grid
        for i in range(5):
            gy = pad + i * (h - 2 * pad) / 4
            val = mx - i * (mx - mn) / 4
            svg.append(f'<line x1="{pad}" y1="{gy:.1f}" x2="{w-pad}" y2="{gy:.1f}" stroke="#eee"/>')
            svg.append(f'<text x="{pad-5}" y="{gy:.1f}" text-anchor="end" font-size="10" fill="#888">{val:.2f}</text>')
        svg.append(f'<polyline fill="none" stroke="#2563eb" stroke-width="2" points="{pts}"/>')
        # x-axis labels (sampled)
        step = max(1, len(labels) // 6)
        for i in range(0, len(labels), step):
            svg.append(f'<text x="{xs[i]:.1f}" y="{h-10}" text-anchor="middle" font-size="10" fill="#888">{html.escape(str(labels[i]))}</text>')
        svg.append("</svg>")
        return "\n".join(svg)

    def _svg_bar(self, data: dict, w: int = 700, h: int = 320) -> str:
        labels = data.get("labels", [])
        values = data.get("values", [])
        if not values:
            return "<p>No data</p>"
        pad = 60
        mn = min(0, min(values))
        mx = max(values) * 1.1 or 1
        n = len(values)
        bar_w = max(4, (w - 2 * pad) / n * 0.7)
        gap = (w - 2 * pad) / n
        zero_y = pad + (mx) / (mx - mn) * (h - 2 * pad) if mn < 0 else h - pad
        svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{w}px">']
        for i, v in enumerate(values):
            x = pad + i * gap + (gap - bar_w) / 2
            bar_h = abs(v) / (mx - mn) * (h - 2 * pad)
            y = zero_y - bar_h if v >= 0 else zero_y
            color = "#22c55e" if v >= 0 else "#ef4444"
            svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}" rx="2"/>')
            if i % max(1, n // 8) == 0 and i < len(labels):
                svg.append(f'<text x="{x + bar_w/2:.1f}" y="{h-10}" text-anchor="middle" font-size="9" fill="#888">{html.escape(str(labels[i]))}</text>')
        svg.append("</svg>")
        return "\n".join(svg)

    def _svg_candlestick(self, data: dict, w: int = 700, h: int = 320) -> str:
        candles = data.get("candles", [])  # list of {open, high, low, close}
        if not candles:
            return "<p>No data</p>"
        pad = 60
        all_vals = [c["high"] for c in candles] + [c["low"] for c in candles]
        mn, mx = min(all_vals), max(all_vals)
        margin = (mx - mn) * 0.05 or 1
        mn -= margin; mx += margin
        n = len(candles)
        cw = max(3, (w - 2 * pad) / n * 0.7)
        gap = (w - 2 * pad) / n

        def ymap(v):
            return pad + (mx - v) / (mx - mn) * (h - 2 * pad)

        svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{w}px">']
        for i, c in enumerate(candles):
            x = pad + i * gap + gap / 2
            color = "#22c55e" if c["close"] >= c["open"] else "#ef4444"
            # wick
            svg.append(f'<line x1="{x:.1f}" y1="{ymap(c["high"]):.1f}" x2="{x:.1f}" y2="{ymap(c["low"]):.1f}" stroke="{color}" stroke-width="1"/>')
            # body
            top = ymap(max(c["open"], c["close"]))
            bot = ymap(min(c["open"], c["close"]))
            bh = max(1, bot - top)
            svg.append(f'<rect x="{x - cw/2:.1f}" y="{top:.1f}" width="{cw:.1f}" height="{bh:.1f}" fill="{color}"/>')
        svg.append("</svg>")
        return "\n".join(svg)

    def _svg_heatmap(self, data: dict, w: int = 700, h: int = 400) -> str:
        matrix = data.get("matrix", [])
        row_labels = data.get("row_labels", [])
        col_labels = data.get("col_labels", [])
        if not matrix:
            return "<p>No data</p>"
        rows = len(matrix)
        cols = len(matrix[0]) if matrix else 0
        pad_l, pad_t = 80, 40
        cw = (w - pad_l) / max(1, cols)
        ch = (h - pad_t) / max(1, rows)
        flat = [v for row in matrix for v in row]
        mn, mx = min(flat), max(flat)
        rng = mx - mn or 1

        def color(v):
            t = (v - mn) / rng
            r = int(255 * (1 - t))
            g = int(200 * t + 55)
            b = int(100)
            return f"rgb({r},{g},{b})"

        svg = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{w}px">']
        for r, row in enumerate(matrix):
            for c, v in enumerate(row):
                x = pad_l + c * cw
                y = pad_t + r * ch
                svg.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{color(v)}" stroke="#fff" stroke-width="1"/>')
                svg.append(f'<text x="{x + cw/2:.1f}" y="{y + ch/2 + 4:.1f}" text-anchor="middle" font-size="10" fill="#333">{v:.1f}</text>')
            if r < len(row_labels):
                svg.append(f'<text x="{pad_l - 5}" y="{pad_t + r * ch + ch/2 + 4:.1f}" text-anchor="end" font-size="10" fill="#888">{html.escape(str(row_labels[r]))}</text>')
        for c in range(cols):
            if c < len(col_labels):
                svg.append(f'<text x="{pad_l + c * cw + cw/2:.1f}" y="{pad_t - 8}" text-anchor="middle" font-size="10" fill="#888">{html.escape(str(col_labels[c]))}</text>')
        svg.append("</svg>")
        return "\n".join(svg)

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def _render_chart(self, spec: _ChartSpec) -> str:
        renderer = {
            "line": self._svg_line,
            "bar": self._svg_bar,
            "candlestick": self._svg_candlestick,
            "heatmap": self._svg_heatmap,
        }[spec.chart_type]
        return f'<div class="card"><h3>{html.escape(spec.title)}</h3>{renderer(spec.data)}</div>'

    def _render_table(self, spec: _TableSpec) -> str:
        hdr = "".join(f"<th>{html.escape(str(h))}</th>" for h in spec.headers)
        rows = ""
        for row in spec.rows:
            cells = "".join(f"<td>{html.escape(str(c))}</td>" for c in row)
            rows += f"<tr>{cells}</tr>\n"
        return f'<div class="card"><h3>{html.escape(spec.title)}</h3><table><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody></table></div>'

    def _render_metrics(self) -> str:
        cards = []
        for m in self._metrics:
            change_html = ""
            if m.change is not None:
                arrow = "▲" if m.change >= 0 else "▼"
                color = "#22c55e" if m.change >= 0 else "#ef4444"
                change_html = f'<span style="color:{color};font-size:14px">{arrow} {m.change:+.2f}%</span>'
            cards.append(
                f'<div class="metric"><div class="metric-name">{html.escape(m.name)}</div>'
                f'<div class="metric-value">{m.value:,.2f}</div>{change_html}</div>'
            )
        return f'<div class="metrics-row">{"".join(cards)}</div>'

    # ------------------------------------------------------------------
    # HTML chrome
    # ------------------------------------------------------------------

    def _html_head(self) -> str:
        return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(self.title)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;padding:24px;color:#333}}
h1{{text-align:center;margin-bottom:24px;color:#1e293b}}
.card{{background:#fff;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.card h3{{margin-bottom:12px;color:#475569}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #e2e8f0}}
th{{background:#f8fafc;font-weight:600}}
.metrics-row{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}}
.metric{{flex:1;min-width:160px;background:#fff;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center}}
.metric-name{{font-size:13px;color:#64748b;margin-bottom:4px}}
.metric-value{{font-size:28px;font-weight:700;color:#1e293b}}
</style></head><body>
<h1>{html.escape(self.title)}</h1>"""

    @staticmethod
    def _html_tail() -> str:
        return "</body></html>"
