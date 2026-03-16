"""
Tearsheet v4.7.0
QuantStats-style tearsheet — standalone HTML with embedded SVG charts.
"""

import html
import math
import os
from datetime import datetime
from typing import Optional


def _cumulative(returns: list[float]) -> list[float]:
    """Cumulative returns curve from daily return series."""
    cum = [1.0]
    for r in returns:
        cum.append(cum[-1] * (1 + r))
    return cum


def _rolling(values: list[float], window: int) -> list[Optional[float]]:
    """Rolling mean."""
    out: list[Optional[float]] = [None] * (window - 1)
    for i in range(window - 1, len(values)):
        out.append(sum(values[i - window + 1: i + 1]) / window)
    return out


def _rolling_sharpe(returns: list[float], window: int = 126, rf: float = 0.0) -> list[Optional[float]]:
    """Rolling annualized Sharpe ratio."""
    out: list[Optional[float]] = [None] * (window - 1)
    for i in range(window - 1, len(returns)):
        w = returns[i - window + 1: i + 1]
        mean = sum(w) / len(w) - rf / 252
        var = sum((r - mean) ** 2 for r in w) / (len(w) - 1) if len(w) > 1 else 0
        std = var ** 0.5
        out.append((mean / std * math.sqrt(252)) if std > 0 else 0)
    return out


def _rolling_vol(returns: list[float], window: int = 63) -> list[Optional[float]]:
    """Rolling annualized volatility."""
    out: list[Optional[float]] = [None] * (window - 1)
    for i in range(window - 1, len(returns)):
        w = returns[i - window + 1: i + 1]
        mean = sum(w) / len(w)
        var = sum((r - mean) ** 2 for r in w) / (len(w) - 1) if len(w) > 1 else 0
        out.append(var ** 0.5 * math.sqrt(252))
    return out


def _underwater(returns: list[float]) -> list[float]:
    """Drawdown (underwater) curve."""
    cum = _cumulative(returns)
    peak = cum[0]
    dd = []
    for v in cum:
        peak = max(peak, v)
        dd.append((v / peak - 1) if peak > 0 else 0)
    return dd


def _monthly_table(returns: list[float]) -> list[dict]:
    """Approximate monthly returns (assumes 21 trading days/month)."""
    months = []
    yr, mo = 2020, 1  # placeholder start
    chunk = 21
    for i in range(0, len(returns), chunk):
        w = returns[i: i + chunk]
        cum = 1.0
        for r in w:
            cum *= 1 + r
        months.append({"year": yr, "month": mo, "return_pct": cum - 1})
        mo += 1
        if mo > 12:
            mo = 1
            yr += 1
    return months


def _annual_returns(returns: list[float]) -> list[tuple[str, float]]:
    """Approximate annual returns (252 days/year)."""
    annual = []
    yr = 2020
    chunk = 252
    for i in range(0, len(returns), chunk):
        w = returns[i: i + chunk]
        cum = 1.0
        for r in w:
            cum *= 1 + r
        annual.append((str(yr), cum - 1))
        yr += 1
    return annual


def _worst_drawdowns(returns: list[float], top_n: int = 5) -> list[dict]:
    """Find worst drawdown periods."""
    cum = _cumulative(returns)
    peak = cum[0]
    peak_idx = 0
    dds = []
    in_dd = False
    dd_start = 0

    for i, v in enumerate(cum):
        if v >= peak:
            if in_dd:
                dds.append({
                    "depth": (min(cum[dd_start:i + 1]) / cum[dd_start] - 1),
                    "start": dd_start,
                    "end": i,
                    "length": i - dd_start,
                })
            peak = v
            peak_idx = i
            in_dd = False
        else:
            if not in_dd:
                dd_start = peak_idx
                in_dd = True

    if in_dd:
        dds.append({
            "depth": (min(cum[dd_start:]) / cum[dd_start] - 1),
            "start": dd_start,
            "end": len(cum) - 1,
            "length": len(cum) - 1 - dd_start,
        })

    dds.sort(key=lambda x: x["depth"])
    return dds[:top_n]


# ─── SVG helpers (lightweight copies) ──────────────────────────

def _svg_line(values, w=900, h=250, color="#00e676", fill="rgba(0,230,118,0.1)", title="", show_zero=False):
    filtered = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(filtered) < 2:
        return '<p style="color:#888">Insufficient data</p>'

    pad = 60
    cw, ch = w - pad * 2, h - pad * 2
    vals = [v for _, v in filtered]
    mn, mx = min(vals), max(vals)
    if mx == mn:
        mx = mn + 1

    def xp(idx):
        return pad + (idx / (len(values) - 1)) * cw

    def yp(v):
        return pad + ch - ((v - mn) / (mx - mn)) * ch

    pts = " ".join(f"{xp(i):.1f},{yp(v):.1f}" for i, v in filtered)
    fill_pts = f"{xp(filtered[0][0]):.1f},{pad + ch} " + pts + f" {xp(filtered[-1][0]):.1f},{pad + ch}"
    ttl = f'<text x="{w / 2}" y="20" text-anchor="middle" fill="#aaa" font-size="13" font-weight="600">{html.escape(title)}</text>' if title else ""
    zl = ""
    if show_zero and mn < 0 < mx:
        yz = yp(0)
        zl = f'<line x1="{pad}" y1="{yz}" x2="{w - pad}" y2="{yz}" stroke="#555" stroke-width="1" stroke-dasharray="4,4"/>'

    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block">
  {ttl}{zl}
  <polygon points="{fill_pts}" fill="{fill}"/>
  <polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
</svg>'''


def _svg_bars(labels, values, w=900, h=220, title=""):
    if not values:
        return ""
    pad = 60
    cw, ch = w - pad * 2, h - pad * 2
    mx = max(abs(v) for v in values) or 1
    bw = max(4, cw / len(values) - 3)
    has_neg = any(v < 0 for v in values)
    zy = pad + ch / 2 if has_neg else pad + ch
    bars = ""
    for i, (l, v) in enumerate(zip(labels, values)):
        x = pad + (i / len(values)) * cw + 1
        bh = abs(v) / mx * (ch / 2 if has_neg else ch)
        y = zy - bh if v >= 0 else zy
        c = "#00e676" if v >= 0 else "#ff5252"
        bars += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{c}" rx="2"/>'
        if len(labels) <= 15:
            bars += f'<text x="{x + bw / 2:.1f}" y="{pad + ch + 14}" text-anchor="middle" fill="#666" font-size="9">{html.escape(l)}</text>'
    ttl = f'<text x="{w / 2}" y="20" text-anchor="middle" fill="#aaa" font-size="13" font-weight="600">{html.escape(title)}</text>' if title else ""
    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block">
  {ttl}{bars}
</svg>'''


def _svg_histogram(values, bins=25, w=900, h=220, title=""):
    if not values:
        return ""
    mn, mx = min(values), max(values)
    if mx == mn:
        mx = mn + 1
    step = (mx - mn) / bins
    counts = [0] * bins
    for v in values:
        counts[min(int((v - mn) / step), bins - 1)] += 1
    mc = max(counts) or 1
    pad = 50
    cw, ch = w - pad * 2, h - pad * 2
    bw = cw / bins
    bars = ""
    for i, c in enumerate(counts):
        x = pad + i * bw
        bh = c / mc * ch
        mid = mn + (i + 0.5) * step
        clr = "#00e676" if mid >= 0 else "#ff5252"
        bars += f'<rect x="{x:.1f}" y="{pad + ch - bh:.1f}" width="{bw - 1:.1f}" height="{bh:.1f}" fill="{clr}" rx="1"/>'
    ttl = f'<text x="{w / 2}" y="18" text-anchor="middle" fill="#aaa" font-size="12">{html.escape(title)}</text>' if title else ""
    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block">
  {ttl}{bars}
</svg>'''


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px;max-width:1100px;margin:0 auto}
h1{color:#58a6ff;margin-bottom:6px;font-size:26px}
h2{color:#58a6ff;margin:24px 0 10px;border-bottom:1px solid #21262d;padding-bottom:6px;font-size:16px}
.sub{color:#8b949e;margin-bottom:24px;font-size:13px}
table{width:100%;border-collapse:collapse;margin:10px 0}
th,td{padding:6px 10px;border:1px solid #21262d;font-size:12px}
th{background:#161b22;color:#58a6ff}
.sec{margin:24px 0}
.footer{margin-top:40px;padding-top:14px;border-top:1px solid #21262d;color:#484f58;font-size:11px;text-align:center}
.ht td{padding:4px 5px;font-size:11px;min-width:52px}
.wdt td{font-size:12px;padding:6px 12px}
"""


# ─── Heatmap helper ────────────────────────────────────────────

def _monthly_heatmap(monthly: list[dict]) -> str:
    if not monthly:
        return "<p>No data</p>"
    by_year: dict[int, dict[int, float]] = {}
    for m in monthly:
        by_year.setdefault(m["year"], {})[m["month"]] = m["return_pct"]
    mos = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    hdr = "<tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in mos) + "<th>Total</th></tr>"
    rows = ""
    for yr in sorted(by_year):
        cells = ""
        tot = 1.0
        for mo in range(1, 13):
            r = by_year[yr].get(mo)
            if r is not None:
                tot *= 1 + r
                p = r * 100
                bg = "#1b5e20" if p > 5 else "#2e7d32" if p > 0 else "#b71c1c" if p > -5 else "#7f0000"
                cells += f'<td style="background:{bg};color:#fff;text-align:center">{p:+.1f}%</td>'
            else:
                cells += '<td style="background:#1a1a2e;color:#444;text-align:center">—</td>'
        yr_r = (tot - 1) * 100
        bg = "#1b5e20" if yr_r > 0 else "#b71c1c"
        cells += f'<td style="background:{bg};color:#fff;text-align:center;font-weight:bold">{yr_r:+.1f}%</td>'
        rows += f"<tr><td style='font-weight:bold'>{yr}</td>{cells}</tr>"
    return f'<table class="ht"><thead>{hdr}</thead><tbody>{rows}</tbody></table>'


class Tearsheet:
    """QuantStats-style standalone tearsheet generator."""

    @staticmethod
    def generate(
        returns: list[float],
        benchmark: Optional[list[float]] = None,
        title: str = "Strategy Tearsheet",
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate standalone HTML tearsheet.

        Args:
            returns: Daily return series (e.g. [0.01, -0.005, ...])
            benchmark: Optional benchmark daily returns
            title: Report title
            output_path: If set, write HTML to file

        Returns:
            HTML string
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cumulative returns
        cum = _cumulative(returns)
        cum_svg = _svg_line(cum, title="Cumulative Returns", color="#00e676")

        bench_svg = ""
        if benchmark and len(benchmark) >= 2:
            bcum = _cumulative(benchmark)
            # Overlay: just show benchmark separately
            bench_svg = _svg_line(bcum, title="Benchmark Cumulative Returns", color="#42a5f5", fill="rgba(66,165,245,0.08)")

        # Rolling Sharpe
        rs = _rolling_sharpe(returns, window=126)
        rs_svg = _svg_line(rs, title="Rolling Sharpe (6mo)", color="#ffc107", fill="rgba(255,193,7,0.08)", show_zero=True)

        # Rolling vol
        rv = _rolling_vol(returns, window=63)
        rv_svg = _svg_line(rv, title="Rolling Volatility (3mo)", color="#ab47bc", fill="rgba(171,71,188,0.08)")

        # Underwater
        uw = _underwater(returns)
        uw_svg = _svg_line(uw, title="Underwater (Drawdown)", color="#ff5252", fill="rgba(255,82,82,0.12)", show_zero=True)

        # Monthly table
        mt = _monthly_table(returns)
        monthly_html = _monthly_heatmap(mt) if mt else "<p>Not enough data</p>"

        # Annual returns bar chart
        annual = _annual_returns(returns)
        ann_svg = _svg_bars([l for l, _ in annual], [v for _, v in annual], title="Annual Returns") if annual else ""

        # Distribution histogram
        dist_svg = _svg_histogram(returns, title="Distribution of Daily Returns") if returns else ""

        # Worst drawdowns table
        worst = _worst_drawdowns(returns, top_n=5)
        wdt_rows = ""
        for i, dd in enumerate(worst):
            wdt_rows += f'<tr><td>{i + 1}</td><td>{dd["depth"] * 100:.2f}%</td><td>{dd["start"]}</td><td>{dd["end"]}</td><td>{dd["length"]} days</td></tr>'
        wdt = f'''<table class="wdt">
  <thead><tr><th>#</th><th>Depth</th><th>Start Idx</th><th>End Idx</th><th>Length</th></tr></thead>
  <tbody>{wdt_rows}</tbody>
</table>''' if worst else "<p>No drawdowns</p>"

        # Summary stats
        total_ret = cum[-1] / cum[0] - 1 if cum else 0
        ann_ret = (1 + total_ret) ** (252 / max(len(returns), 1)) - 1 if returns else 0
        mean_r = sum(returns) / len(returns) if returns else 0
        var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1) if len(returns) > 1 else 0
        vol = var_r ** 0.5 * math.sqrt(252)
        sharpe = (mean_r / (var_r ** 0.5) * math.sqrt(252)) if var_r > 0 else 0
        neg = [r for r in returns if r < 0]
        dvar = sum((r - mean_r) ** 2 for r in neg) / len(neg) if neg else 0
        sortino = (mean_r / (dvar ** 0.5) * math.sqrt(252)) if dvar > 0 else 0
        mdd = min(uw) if uw else 0

        stats_html = f"""<table class="wdt">
<tr><td><b>Total Return</b></td><td>{total_ret * 100:+.2f}%</td><td><b>Sharpe</b></td><td>{sharpe:.3f}</td></tr>
<tr><td><b>Ann. Return</b></td><td>{ann_ret * 100:+.2f}%</td><td><b>Sortino</b></td><td>{sortino:.3f}</td></tr>
<tr><td><b>Volatility</b></td><td>{vol * 100:.2f}%</td><td><b>Max DD</b></td><td>{mdd * 100:.2f}%</td></tr>
<tr><td><b>Trading Days</b></td><td>{len(returns)}</td><td><b>Best Day</b></td><td>{max(returns) * 100:+.2f}%</td></tr>
<tr><td><b>Neg Days</b></td><td>{len(neg)}</td><td><b>Worst Day</b></td><td>{min(returns) * 100:+.2f}%</td></tr>
</table>""" if returns else ""

        out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<h1>🦀 {html.escape(title)}</h1>
<div class="sub">Generated {now} • FinClaw AI Trading Engine</div>

<div class="sec"><h2>📊 Summary Statistics</h2>{stats_html}</div>
<div class="sec"><h2>📈 Cumulative Returns</h2>{cum_svg}{bench_svg}</div>
<div class="sec"><h2>⚡ Rolling Sharpe (6mo)</h2>{rs_svg}</div>
<div class="sec"><h2>📉 Rolling Volatility (3mo)</h2>{rv_svg}</div>
<div class="sec"><h2>🌊 Underwater Plot</h2>{uw_svg}</div>
<div class="sec"><h2>🗓️ Monthly Returns</h2>{monthly_html}</div>
<div class="sec"><h2>📊 Annual Returns</h2>{ann_svg}</div>
<div class="sec"><h2>📊 Distribution of Returns</h2>{dist_svg}</div>
<div class="sec"><h2>💀 Worst Drawdowns</h2>{wdt}</div>

<div class="footer">
  FinClaw v4.7.0 — AI-Powered Financial Intelligence Engine<br>
  <a href="https://github.com/kazhou2024/finclaw" style="color:#58a6ff">github.com/kazhou2024/finclaw</a>
</div>
</body></html>"""

        if output_path:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(out)

        return out
