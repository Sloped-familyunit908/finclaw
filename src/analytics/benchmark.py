"""
FinClaw Benchmark Comparator v3.5.0
Compare strategy performance against market benchmarks.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


class BenchmarkComparator:
    """
    Compare strategy returns against standard benchmarks.

    Calculates alpha, beta, tracking error, information ratio,
    and up/down capture ratios.
    """

    BENCHMARKS = {
        "SPY": "S&P 500",
        "QQQ": "NASDAQ",
        "IWM": "Russell 2000",
        "BTC": "Bitcoin",
        "DIA": "Dow Jones",
        "EFA": "International Developed",
        "AGG": "US Aggregate Bond",
    }

    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self._last_comparison: Optional[dict] = None

    def compare(
        self,
        strategy_returns: list[float],
        benchmark_returns: list[float] = None,
        benchmark: str = "SPY",
    ) -> dict:
        """
        Compare strategy returns against a benchmark.

        Args:
            strategy_returns: List of periodic returns (e.g. daily).
            benchmark_returns: Benchmark return series (same length).
                              If None, generates mock benchmark data.
            benchmark: Benchmark ticker for labeling.

        Returns:
            Dict with alpha, beta, tracking_error, information_ratio,
            up_capture, down_capture, and metadata.
        """
        if benchmark_returns is None:
            benchmark_returns = self._mock_benchmark(len(strategy_returns))

        n = min(len(strategy_returns), len(benchmark_returns))
        sr = strategy_returns[:n]
        br = benchmark_returns[:n]

        if n < 2:
            return self._empty_result(benchmark)

        # Means
        sr_mean = sum(sr) / n
        br_mean = sum(br) / n

        # Covariance and variance
        cov = sum((s - sr_mean) * (b - br_mean) for s, b in zip(sr, br)) / (n - 1)
        var_b = sum((b - br_mean) ** 2 for b in br) / (n - 1)

        beta = cov / var_b if var_b > 0 else 0.0
        # Annualized (assume 252 trading days)
        alpha = (sr_mean - self.risk_free_rate / 252) - beta * (br_mean - self.risk_free_rate / 252)
        alpha_ann = alpha * 252

        # Tracking error
        diffs = [s - b for s, b in zip(sr, br)]
        diff_mean = sum(diffs) / n
        te = math.sqrt(sum((d - diff_mean) ** 2 for d in diffs) / (n - 1)) if n > 1 else 0
        te_ann = te * math.sqrt(252)

        # Information ratio
        ir = (diff_mean * 252) / te_ann if te_ann > 0 else 0.0

        # Capture ratios
        up_capture = self._capture_ratio(sr, br, up=True)
        down_capture = self._capture_ratio(sr, br, up=False)

        result = {
            "benchmark": benchmark,
            "benchmark_name": self.BENCHMARKS.get(benchmark, benchmark),
            "periods": n,
            "alpha": round(alpha_ann, 6),
            "beta": round(beta, 4),
            "tracking_error": round(te_ann, 6),
            "information_ratio": round(ir, 4),
            "up_capture": round(up_capture, 4),
            "down_capture": round(down_capture, 4),
            "strategy_total_return": round(self._total_return(sr), 4),
            "benchmark_total_return": round(self._total_return(br), 4),
        }
        self._last_comparison = result
        return result

    def _capture_ratio(
        self, sr: list[float], br: list[float], up: bool = True
    ) -> float:
        """Calculate up or down capture ratio."""
        pairs = [(s, b) for s, b in zip(sr, br) if (b > 0) == up and b != 0]
        if not pairs:
            return 0.0
        s_sum = sum(s for s, _ in pairs)
        b_sum = sum(b for _, b in pairs)
        return (s_sum / len(pairs)) / (b_sum / len(pairs)) if b_sum != 0 else 0.0

    @staticmethod
    def _total_return(returns: list[float]) -> float:
        cumulative = 1.0
        for r in returns:
            cumulative *= (1 + r)
        return cumulative - 1

    @staticmethod
    def _mock_benchmark(n: int) -> list[float]:
        """Generate mock benchmark returns for testing."""
        import random
        random.seed(42)
        return [random.gauss(0.0004, 0.012) for _ in range(n)]

    def _empty_result(self, benchmark: str) -> dict:
        return {
            "benchmark": benchmark,
            "benchmark_name": self.BENCHMARKS.get(benchmark, benchmark),
            "periods": 0,
            "alpha": 0.0, "beta": 0.0,
            "tracking_error": 0.0, "information_ratio": 0.0,
            "up_capture": 0.0, "down_capture": 0.0,
            "strategy_total_return": 0.0, "benchmark_total_return": 0.0,
        }

    def render_comparison_chart(self) -> str:
        """Render HTML comparison chart from last comparison."""
        if not self._last_comparison:
            return "<p>No comparison data available. Run compare() first.</p>"

        c = self._last_comparison
        return f"""<!DOCTYPE html>
<html><head><title>FinClaw Benchmark Comparison</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; }}
.metric {{ display: flex; justify-content: space-between; padding: 0.5rem 0;
           border-bottom: 1px solid #eee; }}
.label {{ color: #666; }}
.value {{ font-weight: bold; }}
.positive {{ color: #00c853; }}
.negative {{ color: #ff1744; }}
h1 {{ color: #1a237e; }}
.card {{ background: #f5f5f5; border-radius: 12px; padding: 1.5rem; margin: 1rem 0; }}
</style></head>
<body>
<h1>🦀 FinClaw Benchmark Comparison</h1>
<h2>Strategy vs {c['benchmark_name']} ({c['benchmark']})</h2>
<div class="card">
  <div class="metric"><span class="label">Alpha (annualized)</span>
    <span class="value {'positive' if c['alpha'] >= 0 else 'negative'}">{c['alpha']:.4%}</span></div>
  <div class="metric"><span class="label">Beta</span>
    <span class="value">{c['beta']:.3f}</span></div>
  <div class="metric"><span class="label">Tracking Error</span>
    <span class="value">{c['tracking_error']:.4%}</span></div>
  <div class="metric"><span class="label">Information Ratio</span>
    <span class="value">{c['information_ratio']:.3f}</span></div>
  <div class="metric"><span class="label">Up Capture</span>
    <span class="value">{c['up_capture']:.2%}</span></div>
  <div class="metric"><span class="label">Down Capture</span>
    <span class="value">{c['down_capture']:.2%}</span></div>
  <div class="metric"><span class="label">Strategy Return</span>
    <span class="value {'positive' if c['strategy_total_return'] >= 0 else 'negative'}">{c['strategy_total_return']:.2%}</span></div>
  <div class="metric"><span class="label">Benchmark Return</span>
    <span class="value">{c['benchmark_total_return']:.2%}</span></div>
</div>
<p style="color:#999; font-size:0.8rem;">Generated by FinClaw v3.5.0 • {c['periods']} periods</p>
</body></html>"""
