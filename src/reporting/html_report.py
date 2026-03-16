"""
HTML Report Generator v4.9.0
Generate beautiful standalone HTML backtest reports with embedded SVG charts.
No external dependencies — pure HTML/CSS/inline SVG.
"""

import html
import math
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# ─── Data classes ───────────────────────────────────────────────

@dataclass
class Trade:
    """Single trade record."""
    entry_date: str = ""
    exit_date: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl_pct: float = 0.0
    holding_days: int = 0
    side: str = "long"


@dataclass
class BacktestResult:
    """Container for all backtest output data."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    equity_curve: list[float] = field(default_factory=list)
    drawdowns: list[float] = field(default_factory=list)
    monthly_returns: list[dict] = field(default_factory=list)
    trade_log: list[dict] = field(default_factory=list)
    positions: list[float] = field(default_factory=list)  # position size over time
    strategy_name: str = ""
    ticker: str = ""
    start_date: str = ""
    end_date: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        import dataclasses
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "BacktestResult":
        """Deserialize from dict."""
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ─── SVG chart helpers ──────────────────────────────────────────

def _svg_line_chart(
    values: list[float],
    width: int = 900,
    height: int = 280,
    color: str = "#00e676",
    fill_color: str = "rgba(0,230,118,0.12)",
    title: str = "",
    show_zero: bool = False,
    y_format: str = "auto",
) -> str:
    """Generate an inline SVG line chart."""
    if not values or len(values) < 2:
        return '<p style="color:#888">Insufficient data for chart</p>'

    pad = 65
    cw = width - pad * 2
    ch = height - pad * 2

    mn = min(values)
    mx = max(values)
    if mx == mn:
        mx = mn + 1

    def xp(i):
        return pad + (i / (len(values) - 1)) * cw

    def yp(v):
        return pad + ch - ((v - mn) / (mx - mn)) * ch

    points = " ".join(f"{xp(i):.1f},{yp(v):.1f}" for i, v in enumerate(values))
    fill_pts = (
        f"{xp(0):.1f},{pad + ch} " + points + f" {xp(len(values) - 1):.1f},{pad + ch}"
    )

    def fmt(v):
        if y_format == "pct":
            return f"{v * 100:.1f}%"
        if y_format == "dollar":
            return f"${v:,.0f}"
        return f"{v:.2f}" if abs(v) < 100 else f"{v:,.0f}"

    grid = ""
    for i in range(5):
        val = mn + (mx - mn) * i / 4
        y_ = yp(val)
        grid += f'<text x="{pad - 6}" y="{y_ + 4}" text-anchor="end" fill="#666" font-size="10">{fmt(val)}</text>'
        grid += f'<line x1="{pad}" y1="{y_}" x2="{width - pad}" y2="{y_}" stroke="#2a2a3e" stroke-width="0.5"/>'

    zero = ""
    if show_zero and mn < 0 < mx:
        yz = yp(0)
        zero = f'<line x1="{pad}" y1="{yz}" x2="{width - pad}" y2="{yz}" stroke="#555" stroke-width="1" stroke-dasharray="4,4"/>'

    ttl = ""
    if title:
        ttl = f'<text x="{width / 2}" y="22" text-anchor="middle" fill="#aaa" font-size="13" font-weight="600">{html.escape(title)}</text>'

    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block;">
  {ttl}{grid}{zero}
  <polygon points="{fill_pts}" fill="{fill_color}"/>
  <polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
  <circle cx="{xp(0):.1f}" cy="{yp(values[0]):.1f}" r="3" fill="{color}"/>
  <circle cx="{xp(len(values) - 1):.1f}" cy="{yp(values[-1]):.1f}" r="3" fill="{color}"/>
</svg>'''


def _svg_bar_chart(
    labels: list[str],
    values: list[float],
    width: int = 900,
    height: int = 250,
    title: str = "",
) -> str:
    """Vertical bar chart with green/red bars."""
    if not values:
        return '<p style="color:#888">No data</p>'

    pad = 65
    cw = width - pad * 2
    ch = height - pad * 2
    mx = max(abs(v) for v in values) or 1
    bw = max(4, cw / len(values) - 4)

    zero_y = pad + ch / 2 if any(v < 0 for v in values) else pad + ch

    bars = ""
    for i, (lbl, v) in enumerate(zip(labels, values)):
        x = pad + (i / len(values)) * cw + 2
        bar_h = abs(v) / mx * (ch / 2 if any(v2 < 0 for v2 in values) else ch)
        clr = "#00e676" if v >= 0 else "#ff5252"
        y = zero_y - bar_h if v >= 0 else zero_y
        bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" fill="{clr}" rx="2"/>'
        if len(labels) <= 20:
            bars += f'<text x="{x + bw / 2:.1f}" y="{pad + ch + 14}" text-anchor="middle" fill="#666" font-size="9">{html.escape(lbl)}</text>'

    ttl = f'<text x="{width / 2}" y="20" text-anchor="middle" fill="#aaa" font-size="13" font-weight="600">{html.escape(title)}</text>' if title else ""
    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block;">
  {ttl}{bars}
</svg>'''


def _svg_scatter(
    xs: list[float],
    ys: list[float],
    width: int = 400,
    height: int = 300,
    title: str = "",
) -> str:
    """Scatter plot for trade entry/exit analysis."""
    if not xs or not ys or len(xs) != len(ys):
        return '<p style="color:#888">No scatter data</p>'
    pad = 50
    cw = width - pad * 2
    ch = height - pad * 2
    xmn, xmx = min(xs), max(xs)
    ymn, ymx = min(ys), max(ys)
    if xmx == xmn:
        xmx = xmn + 1
    if ymx == ymn:
        ymx = ymn + 1

    dots = ""
    for x, y in zip(xs, ys):
        cx = pad + (x - xmn) / (xmx - xmn) * cw
        cy = pad + ch - (y - ymn) / (ymx - ymn) * ch
        clr = "#00e676" if y > x else "#ff5252"
        dots += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{clr}" opacity="0.7"/>'

    ttl = f'<text x="{width / 2}" y="18" text-anchor="middle" fill="#aaa" font-size="12">{html.escape(title)}</text>' if title else ""
    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:inline-block;">
  {ttl}{dots}
</svg>'''


def _svg_histogram(
    values: list[float],
    bins: int = 20,
    width: int = 400,
    height: int = 250,
    title: str = "",
) -> str:
    """Simple histogram."""
    if not values:
        return '<p style="color:#888">No data</p>'

    mn, mx = min(values), max(values)
    if mx == mn:
        mx = mn + 1
    step = (mx - mn) / bins
    counts = [0] * bins
    for v in values:
        idx = min(int((v - mn) / step), bins - 1)
        counts[idx] += 1

    mc = max(counts) or 1
    pad = 50
    cw = width - pad * 2
    ch = height - pad * 2
    bw = cw / bins

    bars = ""
    for i, c in enumerate(counts):
        x = pad + i * bw
        bh = c / mc * ch
        y = pad + ch - bh
        mid = mn + (i + 0.5) * step
        clr = "#00e676" if mid >= 0 else "#ff5252"
        bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" fill="{clr}" rx="1"/>'

    ttl = f'<text x="{width / 2}" y="18" text-anchor="middle" fill="#aaa" font-size="12">{html.escape(title)}</text>' if title else ""
    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:inline-block;">
  {ttl}{bars}
</svg>'''


# ─── HTML components ────────────────────────────────────────────

def _metric_card(label: str, value: str, color: str = "#00e676") -> str:
    return f'''<div class="mc">
  <div class="mv" style="color:{color}">{value}</div>
  <div class="ml">{label}</div>
</div>'''


def _monthly_heatmap(monthly: list[dict]) -> str:
    """Monthly returns heatmap table."""
    if not monthly:
        return "<p>No monthly data</p>"
    by_year: dict[int, dict[int, float]] = {}
    for m in monthly:
        by_year.setdefault(m.get("year", 0), {})[m.get("month", 1)] = m.get("return_pct", 0)

    mos = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    hdr = "<tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in mos) + "<th>Total</th></tr>"
    rows = ""
    for yr in sorted(by_year):
        cells = ""
        yr_total = 1.0
        for mo in range(1, 13):
            r = by_year[yr].get(mo)
            if r is not None:
                yr_total *= 1 + r
                p = r * 100
                bg = "#1b5e20" if p > 5 else "#2e7d32" if p > 0 else "#b71c1c" if p > -5 else "#7f0000"
                cells += f'<td style="background:{bg};color:#fff;text-align:center">{p:+.1f}%</td>'
            else:
                cells += '<td style="background:#1a1a2e;color:#444;text-align:center">—</td>'
        yr_r = (yr_total - 1) * 100
        bg = "#1b5e20" if yr_r > 0 else "#b71c1c"
        cells += f'<td style="background:{bg};color:#fff;text-align:center;font-weight:bold">{yr_r:+.1f}%</td>'
        rows += f"<tr><td style='font-weight:bold'>{yr}</td>{cells}</tr>"
    return f'<table class="ht"><thead>{hdr}</thead><tbody>{rows}</tbody></table>'


def _trade_log_table(trades: list[dict], max_rows: int = 100) -> str:
    if not trades:
        return "<p>No trades recorded</p>"
    hdr = "<tr><th>#</th><th>Entry</th><th>Exit</th><th>Entry $</th><th>Exit $</th><th>P&L</th><th>Hold</th></tr>"
    rows = ""
    for i, t in enumerate(trades[:max_rows]):
        pnl = t.get("pnl_pct", 0) * 100
        clr = "#00e676" if pnl > 0 else "#ff5252"
        rows += f'''<tr>
  <td>{i + 1}</td>
  <td>{t.get("entry_date", t.get("entry_idx", ""))}</td>
  <td>{t.get("exit_date", t.get("exit_idx", ""))}</td>
  <td>${t.get("entry_price", 0):.2f}</td>
  <td>${t.get("exit_price", 0):.2f}</td>
  <td style="color:{clr}">{pnl:+.2f}%</td>
  <td>{t.get("holding_days", t.get("holding_period", ""))}</td>
</tr>'''
    rem = len(trades) - max_rows
    if rem > 0:
        rows += f'<tr><td colspan="7" style="text-align:center;color:#666">... {rem} more trades</td></tr>'
    return f'<table class="tl"><thead>{hdr}</thead><tbody>{rows}</tbody></table>'


def _risk_metrics_table(result: "BacktestResult") -> str:
    """Comprehensive risk metrics table."""
    rows = [
        ("Total Return", f"{result.total_return * 100:+.2f}%"),
        ("Annualized Return", f"{result.annualized_return * 100:+.2f}%"),
        ("Sharpe Ratio", f"{result.sharpe_ratio:.3f}"),
        ("Sortino Ratio", f"{result.sortino_ratio:.3f}"),
        ("Max Drawdown", f"{result.max_drawdown * 100:.2f}%"),
        ("Win Rate", f"{result.win_rate * 100:.1f}%"),
        ("Profit Factor", f"{result.profit_factor:.3f}"),
        ("Total Trades", str(result.num_trades)),
        ("Avg Trade Return", f"{result.avg_trade_return * 100:+.3f}%"),
        ("Avg Win", f"{result.avg_win * 100:+.3f}%"),
        ("Avg Loss", f"{result.avg_loss * 100:.3f}%"),
    ]
    if result.benchmark_return is not None:
        rows.append(("Benchmark Return", f"{result.benchmark_return * 100:+.2f}%"))
    if result.alpha is not None:
        rows.append(("Alpha", f"{result.alpha * 100:+.3f}%"))

    trs = "".join(f'<tr><td style="font-weight:600">{k}</td><td>{v}</td></tr>' for k, v in rows)
    return f'<table class="risk"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>{trs}</tbody></table>'


# ─── CSS ────────────────────────────────────────────────────────

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px;max-width:1100px;margin:0 auto}
h1{color:#58a6ff;margin-bottom:6px;font-size:28px}
h2{color:#58a6ff;margin:28px 0 12px;border-bottom:1px solid #21262d;padding-bottom:8px;font-size:18px}
.sub{color:#8b949e;margin-bottom:28px;font-size:14px}
.mg{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.mc{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:14px;text-align:center}
.mv{font-size:22px;font-weight:700}
.ml{font-size:11px;color:#8b949e;margin-top:3px;text-transform:uppercase;letter-spacing:0.5px}
table{width:100%;border-collapse:collapse;margin:12px 0}
th,td{padding:7px 10px;border:1px solid #21262d;font-size:12px}
th{background:#161b22;color:#58a6ff;font-weight:600}
.ht td{padding:5px 6px;font-size:11px;min-width:55px}
.tl td{font-family:'SF Mono',Consolas,monospace;font-size:11px}
.risk td{font-size:13px;padding:8px 14px}
.sec{margin:28px 0}
.row{display:flex;gap:16px;flex-wrap:wrap}
.footer{margin-top:48px;padding-top:16px;border-top:1px solid #21262d;color:#484f58;font-size:11px;text-align:center}
@media(max-width:768px){body{padding:16px}.mg{grid-template-columns:repeat(2,1fr)}}
"""


# ─── Main generator ────────────────────────────────────────────

class BacktestReportGenerator:
    """Generate standalone HTML backtest reports."""

    def __init__(self, result: BacktestResult):
        if isinstance(result, dict):
            result = BacktestResult.from_dict(result)
        self.result = result

    def _compute_drawdowns(self) -> list[float]:
        eq = self.result.equity_curve
        if self.result.drawdowns:
            return self.result.drawdowns
        if not eq:
            return []
        dd = []
        peak = eq[0]
        for v in eq:
            peak = max(peak, v)
            dd.append(-((peak - v) / peak) if peak > 0 else 0.0)
        return dd

    def _holding_periods(self) -> list[int]:
        return [t.get("holding_days", t.get("holding_period", 0)) for t in self.result.trade_log if isinstance(t, dict)]

    def generate_html(self, output_path: Optional[str] = None) -> str:
        r = self.result
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"Backtest Report — {r.strategy_name or 'Strategy'}" + (f" ({r.ticker})" if r.ticker else "")

        # Executive Summary metrics
        ret_c = "#00e676" if r.total_return > 0 else "#ff5252"
        sh_c = "#00e676" if r.sharpe_ratio > 1 else ("#ffc107" if r.sharpe_ratio > 0 else "#ff5252")
        wr_c = "#00e676" if r.win_rate > 0.5 else "#ffc107"

        mg = '<div class="mg">'
        mg += _metric_card("Total Return", f"{r.total_return * 100:+.1f}%", ret_c)
        mg += _metric_card("Sharpe Ratio", f"{r.sharpe_ratio:.2f}", sh_c)
        mg += _metric_card("Max Drawdown", f"{r.max_drawdown * 100:.1f}%", "#ff5252")
        mg += _metric_card("Win Rate", f"{r.win_rate * 100:.0f}%", wr_c)
        mg += _metric_card("Profit Factor", f"{r.profit_factor:.2f}", "#00e676" if r.profit_factor > 1.5 else "#ffc107")
        mg += _metric_card("Trades", str(r.num_trades), "#58a6ff")
        mg += _metric_card("Annual Return", f"{r.annualized_return * 100:+.1f}%", ret_c)
        mg += _metric_card("Sortino", f"{r.sortino_ratio:.2f}", sh_c)
        mg += '</div>'

        # Charts
        eq_svg = _svg_line_chart(r.equity_curve, title="Equity Curve", y_format="dollar") if r.equity_curve else ""
        dd = self._compute_drawdowns()
        dd_svg = _svg_line_chart(dd, title="Drawdown", color="#ff5252", fill_color="rgba(255,82,82,0.12)", show_zero=True, y_format="pct") if dd else ""
        heatmap = _monthly_heatmap(r.monthly_returns)
        pos_svg = _svg_line_chart(r.positions, title="Position Sizing Over Time", color="#7c4dff", fill_color="rgba(124,77,255,0.1)") if r.positions and len(r.positions) >= 2 else ""

        # Trade analysis
        entries = [t.get("entry_price", 0) for t in r.trade_log if isinstance(t, dict)]
        exits = [t.get("exit_price", 0) for t in r.trade_log if isinstance(t, dict)]
        scatter = _svg_scatter(entries, exits, title="Entry vs Exit Prices") if entries else ""
        holds = self._holding_periods()
        hist = _svg_histogram([h for h in holds if h], title="Holding Period Distribution") if holds else ""

        trade_tbl = _trade_log_table(r.trade_log)
        risk_tbl = _risk_metrics_table(r)

        out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<h1>🦀 {html.escape(title)}</h1>
<div class="sub">Generated {now} • FinClaw AI Trading Engine{' • ' + r.start_date + ' → ' + r.end_date if r.start_date else ''}</div>

<div class="sec"><h2>📊 Executive Summary</h2>{mg}</div>
<div class="sec"><h2>📈 Equity Curve</h2>{eq_svg}</div>
<div class="sec"><h2>📉 Drawdown</h2>{dd_svg}</div>
<div class="sec"><h2>🗓️ Monthly Returns</h2>{heatmap}</div>
<div class="sec"><h2>🔍 Trade Analysis</h2><div class="row">{scatter}{hist}</div></div>
<div class="sec"><h2>📐 Risk Metrics</h2>{risk_tbl}</div>
{"<div class='sec'><h2>📦 Position Sizing</h2>" + pos_svg + "</div>" if pos_svg else ""}
<div class="sec"><h2>📋 Trade Log</h2>{trade_tbl}</div>

<div class="footer">
  FinClaw v4.9.0 — AI-Powered Financial Intelligence Engine<br>
  <a href="https://github.com/kazhou2024/finclaw" style="color:#58a6ff">github.com/kazhou2024/finclaw</a>
</div>
</body></html>"""

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(out)

        return out
