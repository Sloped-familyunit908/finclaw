"""
Backtest Report Card — One-page graded summary of backtest results.

Assigns a letter grade (A-F) based on risk-adjusted returns and produces
a structured evaluation with strengths, weaknesses, and recommendations.
Optionally renders an HTML report card.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BacktestResult:
    """Minimal backtest result container for the report card.

    Users can pass their own backtest result object as long as it has
    the attributes below (duck typing).
    """
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0
    avg_trade_return: float = 0.0
    calmar_ratio: float = 0.0
    equity_curve: List[float] = field(default_factory=list)


class ReportCard:
    """Generate a graded one-page backtest report card.

    Usage::

        card = ReportCard()
        report = card.generate(my_result, benchmark_result=spy_result)
        html = card.render_html('report.html')
    """

    # Grade thresholds (composite score 0-100 → letter)
    GRADE_THRESHOLDS = [
        (85, 'A'),
        (70, 'B'),
        (55, 'C'),
        (40, 'D'),
        (0,  'F'),
    ]

    def __init__(self):
        self._last_report: Optional[Dict[str, Any]] = None

    def generate(
        self,
        result: Any,
        benchmark_result: Any = None,
    ) -> Dict[str, Any]:
        """Generate a report card from backtest results.

        Parameters
        ----------
        result : BacktestResult or compatible
        benchmark_result : BacktestResult or compatible, optional

        Returns
        -------
        dict with keys: grade, summary, strengths, weaknesses, metrics, recommendation
        """
        metrics = self._extract_metrics(result)
        bench_metrics = self._extract_metrics(benchmark_result) if benchmark_result else None

        score = self._composite_score(metrics, bench_metrics)
        grade = self._score_to_grade(score)

        strengths = self._find_strengths(metrics, bench_metrics)
        weaknesses = self._find_weaknesses(metrics, bench_metrics)
        recommendation = self._make_recommendation(grade, strengths, weaknesses, metrics)
        summary = self._make_summary(grade, metrics, bench_metrics)

        report = {
            'grade': grade,
            'score': round(score, 1),
            'summary': summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'metrics': metrics,
            'recommendation': recommendation,
        }
        if bench_metrics:
            report['benchmark_metrics'] = bench_metrics

        self._last_report = report
        return report

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _composite_score(self, m: Dict, bench: Optional[Dict] = None) -> float:
        """Compute 0-100 composite score from metrics."""
        scores = []

        # Sharpe (weight 25) → 0-25
        sharpe = m.get('sharpe_ratio', 0)
        scores.append(min(25, max(0, sharpe * 10)))

        # Return (weight 20)
        ann_ret = m.get('annualized_return', 0)
        scores.append(min(20, max(0, ann_ret * 100)))

        # Max Drawdown (weight 20) — lower is better
        mdd = abs(m.get('max_drawdown', 0))
        dd_score = max(0, 20 - mdd * 100)
        scores.append(dd_score)

        # Win rate (weight 10)
        wr = m.get('win_rate', 0)
        scores.append(min(10, wr * 10))

        # Profit factor (weight 10)
        pf = m.get('profit_factor', 0)
        scores.append(min(10, max(0, (pf - 0.5) * 5)))

        # Sortino (weight 10)
        sortino = m.get('sortino_ratio', 0)
        scores.append(min(10, max(0, sortino * 4)))

        # Trades count (weight 5) — penalize too few
        n_trades = m.get('num_trades', 0)
        trade_score = min(5, n_trades / 10)
        scores.append(trade_score)

        total = sum(scores)

        # Benchmark bonus/penalty
        if bench:
            bench_ret = bench.get('annualized_return', 0)
            excess = ann_ret - bench_ret
            total += min(5, max(-5, excess * 20))

        return max(0, min(100, total))

    def _score_to_grade(self, score: float) -> str:
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'F'

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _find_strengths(self, m: Dict, bench: Optional[Dict]) -> List[str]:
        strengths = []
        if m.get('sharpe_ratio', 0) > 1.5:
            strengths.append(f"Excellent risk-adjusted returns (Sharpe {m['sharpe_ratio']:.2f})")
        elif m.get('sharpe_ratio', 0) > 1.0:
            strengths.append(f"Good risk-adjusted returns (Sharpe {m['sharpe_ratio']:.2f})")
        if abs(m.get('max_drawdown', 1)) < 0.1:
            strengths.append(f"Low max drawdown ({m['max_drawdown']:.1%})")
        if m.get('win_rate', 0) > 0.6:
            strengths.append(f"High win rate ({m['win_rate']:.1%})")
        if m.get('profit_factor', 0) > 2.0:
            strengths.append(f"Strong profit factor ({m['profit_factor']:.2f})")
        if m.get('sortino_ratio', 0) > 2.0:
            strengths.append(f"Excellent downside protection (Sortino {m['sortino_ratio']:.2f})")
        if bench and m.get('annualized_return', 0) > bench.get('annualized_return', 0):
            excess = m['annualized_return'] - bench['annualized_return']
            strengths.append(f"Outperforms benchmark by {excess:.1%} annually")
        if not strengths:
            strengths.append("Completed backtest successfully")
        return strengths

    def _find_weaknesses(self, m: Dict, bench: Optional[Dict]) -> List[str]:
        weaknesses = []
        if m.get('sharpe_ratio', 0) < 0.5:
            weaknesses.append(f"Poor risk-adjusted returns (Sharpe {m.get('sharpe_ratio', 0):.2f})")
        if abs(m.get('max_drawdown', 0)) > 0.3:
            weaknesses.append(f"Large max drawdown ({m['max_drawdown']:.1%})")
        if m.get('win_rate', 0) < 0.4:
            weaknesses.append(f"Low win rate ({m['win_rate']:.1%})")
        if m.get('num_trades', 0) < 10:
            weaknesses.append(f"Very few trades ({m['num_trades']}) — low statistical significance")
        if m.get('profit_factor', 0) < 1.0:
            weaknesses.append("Profit factor < 1.0 — strategy loses money on average")
        if bench and m.get('annualized_return', 0) < bench.get('annualized_return', 0):
            weaknesses.append("Underperforms benchmark")
        return weaknesses

    def _make_recommendation(self, grade: str, strengths: List[str], weaknesses: List[str], m: Dict) -> str:
        if grade == 'A':
            return "Strategy shows strong performance. Consider paper trading with real-time data before live deployment."
        elif grade == 'B':
            return "Solid strategy with room for improvement. Focus on reducing drawdowns or improving risk-adjusted returns."
        elif grade == 'C':
            return "Average performance. Consider optimizing parameters, adding filters, or combining with other strategies."
        elif grade == 'D':
            return "Below-average results. Significant improvements needed before considering live trading."
        else:
            return "Strategy does not meet minimum performance criteria. Fundamental redesign recommended."

    def _make_summary(self, grade: str, m: Dict, bench: Optional[Dict]) -> str:
        parts = [
            f"Grade: {grade}.",
            f"Annualized return {m.get('annualized_return', 0):.1%}",
            f"with Sharpe {m.get('sharpe_ratio', 0):.2f}",
            f"and max drawdown {m.get('max_drawdown', 0):.1%}.",
            f"{m.get('num_trades', 0)} trades",
            f"at {m.get('win_rate', 0):.0%} win rate.",
        ]
        if bench:
            parts.append(f"Benchmark return: {bench.get('annualized_return', 0):.1%}.")
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Metrics extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_metrics(result: Any) -> Dict[str, Any]:
        """Extract standard metrics from a result object."""
        attrs = [
            'total_return', 'annualized_return', 'sharpe_ratio', 'sortino_ratio',
            'max_drawdown', 'win_rate', 'profit_factor', 'num_trades',
            'avg_trade_return', 'calmar_ratio',
        ]
        m: Dict[str, Any] = {}
        for attr in attrs:
            m[attr] = getattr(result, attr, 0)

        # Compute calmar if missing but we have return and drawdown
        if m['calmar_ratio'] == 0 and m['annualized_return'] != 0 and m['max_drawdown'] != 0:
            m['calmar_ratio'] = m['annualized_return'] / abs(m['max_drawdown'])

        return m

    # ------------------------------------------------------------------
    # HTML rendering
    # ------------------------------------------------------------------

    def render_html(self, output_path: str) -> str:
        """Render the last generated report as an HTML file.

        Parameters
        ----------
        output_path : str
            File path for the HTML output.

        Returns
        -------
        str : the HTML content
        """
        report = self._last_report
        if report is None:
            raise RuntimeError("No report generated yet. Call generate() first.")

        grade = report['grade']
        grade_colors = {'A': '#22c55e', 'B': '#3b82f6', 'C': '#eab308', 'D': '#f97316', 'F': '#ef4444'}
        color = grade_colors.get(grade, '#888')

        strengths_html = ''.join(f'<li class="strength">✅ {s}</li>' for s in report['strengths'])
        weaknesses_html = ''.join(f'<li class="weakness">⚠️ {w}</li>' for w in report['weaknesses'])

        metrics = report['metrics']
        metrics_rows = ''.join(
            f'<tr><td>{k.replace("_", " ").title()}</td><td>{_fmt(v)}</td></tr>'
            for k, v in metrics.items()
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FinClaw Report Card — {grade}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 2em auto; padding: 0 1em; background: #fafafa; color: #333; }}
  .grade {{ display: inline-block; font-size: 4em; font-weight: bold; color: white; background: {color}; border-radius: 16px; width: 100px; height: 100px; line-height: 100px; text-align: center; }}
  .header {{ display: flex; align-items: center; gap: 2em; margin-bottom: 2em; }}
  .summary {{ font-size: 1.1em; color: #555; }}
  h2 {{ border-bottom: 2px solid #ddd; padding-bottom: .3em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: .4em .8em; border-bottom: 1px solid #eee; }}
  tr:nth-child(even) {{ background: #f5f5f5; }}
  .strength {{ color: #16a34a; }}
  .weakness {{ color: #ea580c; }}
  .recommendation {{ background: #eff6ff; padding: 1em; border-radius: 8px; border-left: 4px solid #3b82f6; }}
  footer {{ margin-top: 3em; color: #999; font-size: .85em; }}
</style>
</head>
<body>
<div class="header">
  <div class="grade">{grade}</div>
  <div>
    <h1>FinClaw Report Card</h1>
    <p class="summary">{report['summary']}</p>
  </div>
</div>

<h2>📊 Metrics</h2>
<table>{metrics_rows}</table>

<h2>💪 Strengths</h2>
<ul>{strengths_html}</ul>

<h2>⚠️ Weaknesses</h2>
<ul>{weaknesses_html if weaknesses_html else '<li>None identified</li>'}</ul>

<h2>💡 Recommendation</h2>
<div class="recommendation">{report['recommendation']}</div>

<footer>Generated by FinClaw v3.3.0</footer>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html


def _fmt(v: Any) -> str:
    """Format a metric value for display."""
    if isinstance(v, float):
        if abs(v) < 2 and v != 0:
            return f"{v:.4f}"
        return f"{v:.2f}"
    return str(v)
