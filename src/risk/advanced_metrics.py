"""Advanced Risk Metrics — CVaR, Omega, Tail Ratio, and more."""

import math
from typing import List


class AdvancedRiskMetrics:
    """Collection of advanced risk-adjusted performance metrics."""

    @staticmethod
    def conditional_var(returns: list, confidence: float = 0.95) -> float:
        """Expected Shortfall / CVaR — average loss beyond VaR threshold.

        Args:
            returns: List of period returns.
            confidence: Confidence level (e.g. 0.95 for 95%).

        Returns:
            CVaR as a positive loss number.
        """
        if not returns:
            return 0.0
        sorted_r = sorted(returns)
        cutoff = int(len(sorted_r) * (1 - confidence))
        if cutoff == 0:
            cutoff = 1
        tail = sorted_r[:cutoff]
        return -sum(tail) / len(tail)

    @staticmethod
    def omega_ratio(returns: list, threshold: float = 0.0) -> float:
        """Omega ratio — probability-weighted gain/loss ratio above threshold.

        Args:
            returns: List of period returns.
            threshold: Minimum acceptable return.

        Returns:
            Omega ratio (higher is better).
        """
        if not returns:
            return 0.0
        gains = sum(max(r - threshold, 0) for r in returns)
        losses = sum(max(threshold - r, 0) for r in returns)
        if losses == 0:
            return float('inf') if gains > 0 else 1.0
        return gains / losses

    @staticmethod
    def tail_ratio(returns: list) -> float:
        """Tail ratio — 95th percentile gain / abs(5th percentile loss).

        Measures asymmetry of return distribution tails.
        """
        if len(returns) < 20:
            return 0.0
        sorted_r = sorted(returns)
        n = len(sorted_r)
        p95 = sorted_r[int(n * 0.95)]
        p5 = sorted_r[int(n * 0.05)]
        if p5 == 0:
            return float('inf') if p95 > 0 else 0.0
        return abs(p95 / p5)

    @staticmethod
    def downside_deviation(returns: list, mar: float = 0.0) -> float:
        """Downside deviation — std dev of returns below MAR.

        Args:
            returns: List of period returns.
            mar: Minimum acceptable return.
        """
        if not returns:
            return 0.0
        downside = [(r - mar) ** 2 for r in returns if r < mar]
        if not downside:
            return 0.0
        return math.sqrt(sum(downside) / len(returns))

    @staticmethod
    def information_ratio(returns: list, benchmark: list) -> float:
        """Information ratio — excess return / tracking error.

        Args:
            returns: Portfolio returns.
            benchmark: Benchmark returns.
        """
        if not returns or not benchmark or len(returns) != len(benchmark):
            return 0.0
        excess = [r - b for r, b in zip(returns, benchmark)]
        mean_excess = sum(excess) / len(excess)
        if len(excess) < 2:
            return 0.0
        var = sum((e - mean_excess) ** 2 for e in excess) / (len(excess) - 1)
        te = math.sqrt(var)
        if te == 0:
            return 0.0
        return mean_excess / te

    @staticmethod
    def treynor_ratio(returns: list, benchmark: list, rf: float = 0.0) -> float:
        """Treynor ratio — excess return / portfolio beta.

        Args:
            returns: Portfolio returns.
            benchmark: Benchmark returns.
            rf: Risk-free rate per period.
        """
        if not returns or not benchmark or len(returns) != len(benchmark):
            return 0.0
        n = len(returns)
        mean_r = sum(returns) / n
        mean_b = sum(benchmark) / n
        cov = sum((r - mean_r) * (b - mean_b) for r, b in zip(returns, benchmark)) / n
        var_b = sum((b - mean_b) ** 2 for b in benchmark) / n
        if var_b == 0:
            return 0.0
        beta = cov / var_b
        if beta == 0:
            return 0.0
        return (mean_r - rf) / beta

    @staticmethod
    def capture_ratio(returns: list, benchmark: list) -> dict:
        """Up/down capture ratios — how much of benchmark moves are captured.

        Args:
            returns: Portfolio returns.
            benchmark: Benchmark returns.

        Returns:
            Dict with up_capture, down_capture, capture_ratio.
        """
        if not returns or not benchmark or len(returns) != len(benchmark):
            return {'up_capture': 0.0, 'down_capture': 0.0, 'capture_ratio': 0.0}

        up_port = [r for r, b in zip(returns, benchmark) if b > 0]
        up_bench = [b for b in benchmark if b > 0]
        down_port = [r for r, b in zip(returns, benchmark) if b < 0]
        down_bench = [b for b in benchmark if b < 0]

        up_capture = (sum(up_port) / sum(up_bench) * 100) if up_bench and sum(up_bench) != 0 else 0.0
        down_capture = (sum(down_port) / sum(down_bench) * 100) if down_bench and sum(down_bench) != 0 else 0.0

        capture = up_capture / down_capture if down_capture != 0 else 0.0

        return {
            'up_capture': round(up_capture, 2),
            'down_capture': round(down_capture, 2),
            'capture_ratio': round(capture, 2),
        }
