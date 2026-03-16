"""
Strategy Comparison v4.7.0
Compare multiple strategies side-by-side with overlaid equity curves.
"""

import html
import math
import os
from datetime import datetime
from typing import Optional


COLORS = ["#00e676", "#42a5f5", "#ff5252", "#ffc107", "#ab47bc", "#26c6da", "#ef5350", "#66bb6a", "#ffa726", "#8d6e63"]


def _calc_metrics(returns: list[float]) -> dict:
    """Calculate comprehensive metrics from daily returns."""
    if not returns:
        return {}
    n = len(returns)
    cum = 1.0
    for r in returns:
        cum *= 1 + r
    total = cum - 1
    ann = (cum ** (252 / n) - 1) if n > 0 else 0

    mean = sum(returns) / n
    var = sum((r - mean) ** 2 for r in returns) / (n - 1) if n > 1 else 0
    std = var ** 0.5
    vol = std * math.sqrt(252)
    sharpe = (mean / std * math.sqrt(252)) if std > 0 else 0

    neg = [r for r in returns if r < 0]
    dvar = sum((r - mean) ** 2 for r in neg) / len(neg) if neg else 0
    sortino = (mean / (dvar ** 0.5) * math.sqrt(252)) if dvar > 0 else 0

    # Max drawdown
    peak = 1.0
    mdd = 0.0
    cv = 1.0
    for r in returns:
        cv *= 1 + r
        peak = max(peak, cv)
        dd = (peak - cv) / peak
        mdd = max(mdd, dd)

    # Win rate
    wins = sum(1 for r in returns if r > 0)
    win_rate = wins / n if n > 0 else 0

    # Profit factor
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Calmar
    calmar = ann / mdd if mdd > 0 else float("inf")

    return {
        "total_return": total,
        "annualized_return": ann,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": mdd,
        "volatility": vol,
        "calmar_ratio": calmar,
        "win_rate": win_rate,
        "profit_factor": pf,
        "num_days": n,
    }


def _cumulative(returns: list[float]) -> list[float]:
    cum = [1.0]
    for r in returns:
        cum.append(cum[-1] * (1 + r))
    return cum


class StrategyComparison:
    """Compare multiple strategies with metrics and HTML report."""

    def __init__(self):
        self._strategies: list[tuple[str, list[float]]] = []

    def add_strategy(self, name: str, returns: list[float]):
        """Add a strategy's daily returns for comparison."""
        self._strategies.append((name, returns))

    def compare(self) -> dict:
        """
        Side-by-side metrics comparison.

        Returns:
            dict with 'strategies' list and 'best_overall' name
        """
        results = []
        for name, rets in self._strategies:
            m = _calc_metrics(rets)
            m["name"] = name
            results.append(m)

        # Rank by composite score: sharpe * 0.4 + sortino * 0.3 + calmar * 0.3 (normalized)
        best = ""
        best_score = float("-inf")
        for m in results:
            score = m.get("sharpe_ratio", 0) * 0.4 + m.get("sortino_ratio", 0) * 0.3
            cal = m.get("calmar_ratio", 0)
            if cal != float("inf"):
                score += cal * 0.3
            if score > best_score:
                best_score = score
                best = m["name"]

        return {"strategies": results, "best_overall": best}

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Generate HTML comparison report with overlaid equity curves."""
        comp = self.compare()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Overlaid equity curves SVG
        w, h = 900, 320
        pad = 65
        cw, ch = w - pad * 2, h - pad * 2

        curves = []
        all_vals = []
        for name, rets in self._strategies:
            c = _cumulative(rets)
            curves.append((name, c))
            all_vals.extend(c)

        mn = min(all_vals) if all_vals else 0
        mx = max(all_vals) if all_vals else 1
        if mx == mn:
            mx = mn + 1

        lines = ""
        legend = ""
        for idx, (name, c) in enumerate(curves):
            color = COLORS[idx % len(COLORS)]
            if len(c) < 2:
                continue
            pts = " ".join(
                f"{pad + (i / (len(c) - 1)) * cw:.1f},{pad + ch - ((v - mn) / (mx - mn)) * ch:.1f}"
                for i, v in enumerate(c)
            )
            lines += f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
            ly = 28 + idx * 16
            legend += f'<rect x="{pad}" y="{ly}" width="12" height="3" fill="{color}" rx="1"/>'
            legend += f'<text x="{pad + 16}" y="{ly + 4}" fill="#aaa" font-size="11">{html.escape(name)}</text>'

        # Grid
        grid = ""
        for i in range(5):
            v = mn + (mx - mn) * i / 4
            y = pad + ch - ((v - mn) / (mx - mn)) * ch
            grid += f'<text x="{pad - 6}" y="{y + 4}" text-anchor="end" fill="#666" font-size="10">{v:.2f}</text>'
            grid += f'<line x1="{pad}" y1="{y}" x2="{w - pad}" y2="{y}" stroke="#2a2a3e" stroke-width="0.5"/>'

        eq_svg = f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg"
  style="background:#12121f;border-radius:10px;margin:10px 0;display:block">
  <text x="{w / 2}" y="20" text-anchor="middle" fill="#aaa" font-size="13" font-weight="600">Equity Curves Comparison</text>
  {grid}{lines}{legend}
</svg>'''

        # Metrics table
        hdr = "<tr><th>Strategy</th><th>Return</th><th>Ann.</th><th>Sharpe</th><th>Sortino</th><th>MaxDD</th><th>Vol</th><th>Calmar</th><th>Win%</th><th>PF</th></tr>"
        rows = ""
        for idx, m in enumerate(comp["strategies"]):
            color = COLORS[idx % len(COLORS)]
            cal = m.get("calmar_ratio", 0)
            cal_s = f"{cal:.2f}" if cal != float("inf") else "∞"
            pf = m.get("profit_factor", 0)
            pf_s = f"{pf:.2f}" if pf != float("inf") else "∞"
            rows += f'''<tr>
  <td><span style="color:{color};font-weight:700">●</span> {html.escape(m["name"])}</td>
  <td>{m["total_return"] * 100:+.1f}%</td>
  <td>{m["annualized_return"] * 100:+.1f}%</td>
  <td>{m["sharpe_ratio"]:.2f}</td>
  <td>{m["sortino_ratio"]:.2f}</td>
  <td>{m["max_drawdown"] * 100:.1f}%</td>
  <td>{m["volatility"] * 100:.1f}%</td>
  <td>{cal_s}</td>
  <td>{m["win_rate"] * 100:.0f}%</td>
  <td>{pf_s}</td>
</tr>'''

        best = comp.get("best_overall", "")

        out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Strategy Comparison</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px;max-width:1100px;margin:0 auto}}
h1{{color:#58a6ff;margin-bottom:6px;font-size:26px}}
h2{{color:#58a6ff;margin:24px 0 10px;border-bottom:1px solid #21262d;padding-bottom:6px;font-size:16px}}
.sub{{color:#8b949e;margin-bottom:24px;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin:10px 0}}
th,td{{padding:7px 10px;border:1px solid #21262d;font-size:12px}}
th{{background:#161b22;color:#58a6ff;font-weight:600}}
.sec{{margin:24px 0}}
.best{{background:#161b22;border:1px solid #00e676;border-radius:10px;padding:14px;margin:14px 0;color:#00e676;font-size:16px;font-weight:700;text-align:center}}
.footer{{margin-top:40px;padding-top:14px;border-top:1px solid #21262d;color:#484f58;font-size:11px;text-align:center}}
</style>
</head>
<body>
<h1>🦀 Strategy Comparison</h1>
<div class="sub">Generated {now} • {len(self._strategies)} strategies • FinClaw AI Trading Engine</div>

<div class="sec"><h2>📈 Equity Curves</h2>{eq_svg}</div>

<div class="sec"><h2>📊 Performance Metrics</h2>
<table><thead>{hdr}</thead><tbody>{rows}</tbody></table>
</div>

{"<div class='best'>🏆 Best Overall: " + html.escape(best) + "</div>" if best else ""}

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
