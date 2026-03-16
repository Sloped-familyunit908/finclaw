"""
HTML Report Generator
Generate beautiful standalone HTML backtest reports with inline SVG charts.
No external dependencies — pure HTML/CSS/inline SVG.
"""

import html
import math
import json
import os
from datetime import datetime
from typing import Any, Optional


def _svg_line_chart(
    values: list[float],
    width: int = 800,
    height: int = 250,
    color: str = "#00e676",
    fill_color: str = "rgba(0,230,118,0.15)",
    title: str = "",
    show_zero: bool = False,
) -> str:
    """Generate an inline SVG line chart."""
    if not values or len(values) < 2:
        return "<p>No data</p>"

    padding = 60
    chart_w = width - padding * 2
    chart_h = height - padding * 2

    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v = min_v + 1

    def x(i):
        return padding + (i / (len(values) - 1)) * chart_w

    def y(v):
        return padding + chart_h - ((v - min_v) / (max_v - min_v)) * chart_h

    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    fill_points = f"{x(0):.1f},{padding + chart_h} " + points + f" {x(len(values)-1):.1f},{padding + chart_h}"

    # Y-axis labels
    y_labels = ""
    for i in range(5):
        val = min_v + (max_v - min_v) * i / 4
        yp = y(val)
        label = f"{val:.2f}" if abs(val) < 100 else f"{val:,.0f}"
        y_labels += f'<text x="{padding-5}" y="{yp}" text-anchor="end" fill="#888" font-size="11">{label}</text>'
        y_labels += f'<line x1="{padding}" y1="{yp}" x2="{width-padding}" y2="{yp}" stroke="#333" stroke-width="0.5"/>'

    zero_line = ""
    if show_zero and min_v < 0 < max_v:
        yz = y(0)
        zero_line = f'<line x1="{padding}" y1="{yz}" x2="{width-padding}" y2="{yz}" stroke="#666" stroke-width="1" stroke-dasharray="4,4"/>'

    title_svg = ""
    if title:
        title_svg = f'<text x="{width/2}" y="20" text-anchor="middle" fill="#ccc" font-size="14" font-weight="bold">{html.escape(title)}</text>'

    return f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#1a1a2e;border-radius:8px;margin:8px 0;">
  {title_svg}
  {y_labels}
  {zero_line}
  <polygon points="{fill_points}" fill="{fill_color}"/>
  <polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>
  <circle cx="{x(0):.1f}" cy="{y(values[0]):.1f}" r="3" fill="{color}"/>
  <circle cx="{x(len(values)-1):.1f}" cy="{y(values[-1]):.1f}" r="3" fill="{color}"/>
</svg>'''


def _monthly_heatmap(monthly_returns: list[dict]) -> str:
    """Generate monthly returns heatmap as HTML table."""
    if not monthly_returns:
        return "<p>No monthly data</p>"

    # Group by year/month
    by_year: dict[int, dict[int, float]] = {}
    for m in monthly_returns:
        yr = m.get("year", 0)
        mo = m.get("month", 1)
        by_year.setdefault(yr, {})[mo] = m.get("return_pct", 0)

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    header = "<tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in months) + "<th>Total</th></tr>"
    rows = ""
    for yr in sorted(by_year):
        cells = ""
        yr_total = 1.0
        for mo in range(1, 13):
            ret = by_year[yr].get(mo)
            if ret is not None:
                yr_total *= (1 + ret)
                pct = ret * 100
                if pct > 5:
                    bg = "#1b5e20"
                elif pct > 0:
                    bg = "#2e7d32"
                elif pct > -5:
                    bg = "#b71c1c"
                else:
                    bg = "#7f0000"
                cells += f'<td style="background:{bg};color:#fff;text-align:center">{pct:+.1f}%</td>'
            else:
                cells += '<td style="background:#222;color:#555;text-align:center">—</td>'
        yr_ret = (yr_total - 1) * 100
        yr_bg = "#1b5e20" if yr_ret > 0 else "#b71c1c"
        cells += f'<td style="background:{yr_bg};color:#fff;text-align:center;font-weight:bold">{yr_ret:+.1f}%</td>'
        rows += f"<tr><td style='font-weight:bold'>{yr}</td>{cells}</tr>"

    return f'''<table class="heatmap">
  <thead>{header}</thead>
  <tbody>{rows}</tbody>
</table>'''


def _metric_card(label: str, value: str, color: str = "#00e676") -> str:
    return f'''<div class="metric-card">
  <div class="metric-value" style="color:{color}">{value}</div>
  <div class="metric-label">{label}</div>
</div>'''


def _trade_log_table(trades: list[dict], max_rows: int = 50) -> str:
    """Trade log HTML table."""
    if not trades:
        return "<p>No trades</p>"

    header = "<tr><th>#</th><th>Entry</th><th>Exit</th><th>Entry $</th><th>Exit $</th><th>P&L</th><th>Hold</th></tr>"
    rows = ""
    for i, t in enumerate(trades[:max_rows]):
        pnl = t.get("pnl_pct", 0) * 100
        color = "#00e676" if pnl > 0 else "#ff5252"
        rows += f'''<tr>
  <td>{i+1}</td>
  <td>{t.get("entry_idx", "")}</td>
  <td>{t.get("exit_idx", "")}</td>
  <td>${t.get("entry_price", 0):.2f}</td>
  <td>${t.get("exit_price", 0):.2f}</td>
  <td style="color:{color}">{pnl:+.2f}%</td>
  <td>{t.get("holding_period", "")}</td>
</tr>'''

    remaining = len(trades) - max_rows
    if remaining > 0:
        rows += f'<tr><td colspan="7" style="text-align:center;color:#888">... and {remaining} more trades</td></tr>'

    return f'''<table class="trade-log">
  <thead>{header}</thead>
  <tbody>{rows}</tbody>
</table>'''


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 32px; }
h1 { color: #58a6ff; margin-bottom: 8px; }
h2 { color: #58a6ff; margin: 24px 0 12px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }
.subtitle { color: #8b949e; margin-bottom: 24px; }
.metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 16px 0; }
.metric-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 16px; text-align: center; }
.metric-value { font-size: 24px; font-weight: bold; }
.metric-label { font-size: 12px; color: #8b949e; margin-top: 4px; text-transform: uppercase; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; }
th, td { padding: 8px 12px; border: 1px solid #21262d; font-size: 13px; }
th { background: #161b22; color: #58a6ff; }
.heatmap td { padding: 6px 8px; font-size: 12px; min-width: 60px; }
.trade-log td { font-family: monospace; font-size: 12px; }
.section { margin: 24px 0; }
.footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #21262d; color: #484f58; font-size: 12px; text-align: center; }
"""


def _tca_section(tca_data: Optional[dict]) -> str:
    """Render TCA section if data present."""
    if not tca_data:
        return ""
    return f'''<div class="section">
  <h2>💰 Transaction Cost Analysis</h2>
  <div class="metrics-grid">
    {_metric_card("Total Cost", f"{tca_data.get('total_cost_bps', 0):.1f} bps", "#ffc107")}
    {_metric_card("Commission", f"${tca_data.get('commission_cost', 0):,.2f}", "#ffc107")}
    {_metric_card("Slippage", f"${tca_data.get('slippage_cost', 0):,.2f}", "#ffc107")}
    {_metric_card("Market Impact", f"${tca_data.get('market_impact', 0):,.2f}", "#ffc107")}
    {_metric_card("Opportunity", f"${tca_data.get('opportunity_cost', 0):,.2f}", "#ffc107")}
    {_metric_card("Cost/Return", f"{tca_data.get('cost_as_pct_of_gross_return', 0):.1%}", "#ff5252")}
  </div>
</div>'''


def _comparison_section(comp_data: Optional[dict]) -> str:
    """Render strategy comparison table if data present."""
    if not comp_data or not comp_data.get("strategies"):
        return ""
    header = "<tr><th>Strategy</th><th>Return</th><th>CAGR</th><th>Sharpe</th><th>Sortino</th><th>MaxDD</th><th>Win%</th><th>PF</th></tr>"
    rows = ""
    for s in comp_data["strategies"]:
        rows += f'''<tr>
  <td><b>{html.escape(s.get("name", ""))}</b></td>
  <td>{s.get("total_return", 0)*100:+.1f}%</td>
  <td>{s.get("cagr", 0)*100:+.1f}%</td>
  <td>{s.get("sharpe_ratio", 0):.2f}</td>
  <td>{s.get("sortino_ratio", 0):.2f}</td>
  <td>{s.get("max_drawdown", 0)*100:.1f}%</td>
  <td>{s.get("win_rate", 0)*100:.0f}%</td>
  <td>{s.get("profit_factor", 0):.2f}</td>
</tr>'''
    best = comp_data.get("best_overall", "")
    return f'''<div class="section">
  <h2>🏆 Strategy Comparison</h2>
  <table><thead>{header}</thead><tbody>{rows}</tbody></table>
  {"<p>🏆 Best Overall: <b>" + html.escape(best) + "</b></p>" if best else ""}
</div>'''


def generate_html_report(
    report_data: dict[str, Any],
    title: str = "FinClaw Backtest Report",
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a standalone HTML backtest report.
    
    Args:
        report_data: Dict with keys: total_return, annualized_return, sharpe_ratio,
                     sortino_ratio, max_drawdown, win_rate, profit_factor, num_trades,
                     avg_trade_return, avg_win, avg_loss, equity_curve, monthly_returns,
                     trade_log, benchmark_return, alpha
        title: Report title
        output_path: If set, write HTML to this file
    
    Returns:
        HTML string
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Metrics
    total_ret = report_data.get("total_return", 0)
    ann_ret = report_data.get("annualized_return", 0)
    sharpe = report_data.get("sharpe_ratio", 0)
    sortino = report_data.get("sortino_ratio", 0)
    mdd = report_data.get("max_drawdown", 0)
    win_rate = report_data.get("win_rate", 0)
    pf = report_data.get("profit_factor", 0)
    n_trades = report_data.get("num_trades", 0)
    avg_trade = report_data.get("avg_trade_return", 0)
    avg_win = report_data.get("avg_win", 0)
    avg_loss = report_data.get("avg_loss", 0)
    bench_ret = report_data.get("benchmark_return")
    alpha = report_data.get("alpha")

    # Colors
    ret_color = "#00e676" if total_ret > 0 else "#ff5252"
    sharpe_color = "#00e676" if sharpe > 1 else ("#ffc107" if sharpe > 0 else "#ff5252")

    metrics_html = '<div class="metrics-grid">'
    metrics_html += _metric_card("Total Return", f"{total_ret*100:+.1f}%", ret_color)
    metrics_html += _metric_card("Annual Return", f"{ann_ret*100:+.1f}%", ret_color)
    metrics_html += _metric_card("Sharpe Ratio", f"{sharpe:.2f}", sharpe_color)
    metrics_html += _metric_card("Sortino Ratio", f"{sortino:.2f}", sharpe_color)
    metrics_html += _metric_card("Max Drawdown", f"{mdd*100:.1f}%", "#ff5252")
    metrics_html += _metric_card("Win Rate", f"{win_rate*100:.0f}%", "#00e676" if win_rate > 0.5 else "#ffc107")
    metrics_html += _metric_card("Profit Factor", f"{pf:.2f}", "#00e676" if pf > 1.5 else "#ffc107")
    metrics_html += _metric_card("Trades", str(n_trades), "#58a6ff")
    metrics_html += _metric_card("Avg Trade", f"{avg_trade*100:+.2f}%", "#00e676" if avg_trade > 0 else "#ff5252")
    metrics_html += _metric_card("Avg Win", f"{avg_win*100:+.2f}%", "#00e676")
    metrics_html += _metric_card("Avg Loss", f"{avg_loss*100:.2f}%", "#ff5252")
    if bench_ret is not None:
        metrics_html += _metric_card("Benchmark", f"{bench_ret*100:+.1f}%", "#8b949e")
    if alpha is not None:
        metrics_html += _metric_card("Alpha", f"{alpha*100:+.2f}%", "#00e676" if alpha > 0 else "#ff5252")
    metrics_html += '</div>'

    # Equity curve
    equity = report_data.get("equity_curve", [])
    equity_svg = _svg_line_chart(equity, title="Equity Curve", color="#00e676") if equity else ""

    # Drawdown chart
    dd_values = []
    if equity:
        peak = equity[0]
        for e in equity:
            peak = max(peak, e)
            dd_values.append(-((peak - e) / peak) if peak > 0 else 0)
    dd_svg = _svg_line_chart(dd_values, title="Drawdown", color="#ff5252",
                              fill_color="rgba(255,82,82,0.15)", show_zero=True) if dd_values else ""

    # Monthly heatmap
    monthly = report_data.get("monthly_returns", [])
    if monthly and isinstance(monthly[0], dict):
        monthly_html = _monthly_heatmap(monthly)
    else:
        monthly_html = "<p>No monthly return data</p>"

    # Trade log
    trades = report_data.get("trade_log", [])
    if trades:
        if hasattr(trades[0], "__dict__"):
            trades = [t.__dict__ if hasattr(t, "__dict__") else t for t in trades]
    trade_html = _trade_log_table(trades)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <h1>🦀 {html.escape(title)}</h1>
  <div class="subtitle">Generated {now} by FinClaw AI Trading Engine</div>

  <div class="section">
    <h2>📊 Key Metrics</h2>
    {metrics_html}
  </div>

  <div class="section">
    <h2>📈 Equity Curve</h2>
    {equity_svg}
  </div>

  <div class="section">
    <h2>📉 Drawdown</h2>
    {dd_svg}
  </div>

  <div class="section">
    <h2>🗓️ Monthly Returns</h2>
    {monthly_html}
  </div>

  <div class="section">
    <h2>📋 Trade Log</h2>
    {trade_html}
  </div>

  {_tca_section(report_data.get("tca"))}
  {_comparison_section(report_data.get("comparison"))}

  <div class="footer">
    FinClaw v2.3.0 — AI-Powered Financial Intelligence Engine<br>
    <a href="https://github.com/NeuZhou/finclaw" style="color:#58a6ff">github.com/NeuZhou/finclaw</a>
  </div>
</body>
</html>"""

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    return html_content
