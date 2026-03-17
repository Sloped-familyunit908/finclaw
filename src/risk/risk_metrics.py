"""
Comprehensive Risk Metrics Calculator.

Sharpe, Sortino, Max Drawdown, VaR, CVaR, Calmar, Win Rate,
Profit Factor, Risk-Reward Ratio — all in one place.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class DrawdownInfo:
    """Detailed drawdown information."""
    max_drawdown: float          # worst peak-to-trough (negative)
    max_drawdown_duration: int   # bars in longest drawdown
    current_drawdown: float
    drawdown_series: list[float]


@dataclass
class RiskReport:
    """Complete risk report for a return series."""
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    var_95: float
    cvar_95: float
    var_99: float
    cvar_99: float
    win_rate: float
    profit_factor: float
    risk_reward_ratio: float
    num_trades: int
    skewness: float
    kurtosis: float


class RiskMetrics:
    """
    Collection of risk metric calculators.

    All methods are static — pass in return series or trade P&L lists.
    Assumes daily returns unless `periods_per_year` is overridden.
    """

    @staticmethod
    def sharpe_ratio(
        returns: list[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """
        Annualized Sharpe Ratio.

        Args:
            returns: List of period returns (e.g. daily).
            risk_free_rate: Annualized risk-free rate.
            periods_per_year: Trading periods per year (252 for daily).

        Returns:
            Sharpe ratio (higher is better).
        """
        if len(returns) < 2:
            return 0.0
        rf_period = risk_free_rate / periods_per_year
        excess = [r - rf_period for r in returns]
        mean_excess = sum(excess) / len(excess)
        var = sum((e - mean_excess) ** 2 for e in excess) / (len(excess) - 1)
        std = math.sqrt(var)
        if std == 0:
            return 0.0
        return (mean_excess / std) * math.sqrt(periods_per_year)

    @staticmethod
    def sortino_ratio(
        returns: list[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """
        Annualized Sortino Ratio — penalizes only downside volatility.

        Args:
            returns: List of period returns.
            risk_free_rate: Annualized risk-free rate.
            periods_per_year: Trading periods per year.

        Returns:
            Sortino ratio (higher is better).
        """
        if len(returns) < 2:
            return 0.0
        rf_period = risk_free_rate / periods_per_year
        excess = [r - rf_period for r in returns]
        mean_excess = sum(excess) / len(excess)
        downside = [(min(e, 0)) ** 2 for e in excess]
        down_dev = math.sqrt(sum(downside) / len(downside))
        if down_dev == 0:
            return float('inf') if mean_excess > 0 else 0.0
        return (mean_excess / down_dev) * math.sqrt(periods_per_year)

    @staticmethod
    def max_drawdown(returns: list[float]) -> DrawdownInfo:
        """
        Compute max drawdown and duration from a return series.

        Args:
            returns: List of period returns.

        Returns:
            DrawdownInfo with max drawdown, duration, and full series.
        """
        if not returns:
            return DrawdownInfo(0.0, 0, 0.0, [])

        equity = [1.0]
        for r in returns:
            equity.append(equity[-1] * (1 + r))

        peak = equity[0]
        max_dd = 0.0
        dd_series = []
        current_dd_start = 0
        max_dd_duration = 0
        in_drawdown = False
        dd_start_idx = 0

        for i, eq in enumerate(equity):
            if eq >= peak:
                peak = eq
                if in_drawdown:
                    duration = i - dd_start_idx
                    max_dd_duration = max(max_dd_duration, duration)
                    in_drawdown = False
            dd = (eq - peak) / peak if peak > 0 else 0.0
            dd_series.append(dd)
            if dd < max_dd:
                max_dd = dd
            if dd < 0 and not in_drawdown:
                in_drawdown = True
                dd_start_idx = i

        if in_drawdown:
            max_dd_duration = max(max_dd_duration, len(equity) - dd_start_idx)

        current_dd = dd_series[-1] if dd_series else 0.0

        return DrawdownInfo(
            max_drawdown=max_dd,
            max_drawdown_duration=max_dd_duration,
            current_drawdown=current_dd,
            drawdown_series=dd_series,
        )

    @staticmethod
    def value_at_risk(
        returns: list[float],
        confidence: float = 0.95,
        method: str = "historical",
    ) -> float:
        """
        Value at Risk — the worst expected loss at a given confidence level.

        Args:
            returns: List of period returns.
            confidence: Confidence level (e.g. 0.95 for 95%).
            method: "historical" or "parametric".

        Returns:
            VaR as a negative number (e.g. -0.025 means 2.5% loss).
        """
        if len(returns) < 10:
            return 0.0

        if method == "parametric":
            mean = sum(returns) / len(returns)
            std = math.sqrt(
                sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
            )
            z_map = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
            z = z_map.get(confidence, 1.645)
            return mean - z * std
        else:
            # Historical
            sorted_r = sorted(returns)
            idx = int(len(sorted_r) * (1 - confidence))
            idx = max(0, min(idx, len(sorted_r) - 1))
            return sorted_r[idx]

    @staticmethod
    def conditional_var(
        returns: list[float],
        confidence: float = 0.95,
    ) -> float:
        """
        Conditional VaR (Expected Shortfall) — average loss beyond VaR.

        Args:
            returns: List of period returns.
            confidence: Confidence level.

        Returns:
            CVaR as a negative number.
        """
        if len(returns) < 10:
            return 0.0
        sorted_r = sorted(returns)
        cutoff = max(int(len(sorted_r) * (1 - confidence)), 1)
        tail = sorted_r[:cutoff]
        return sum(tail) / len(tail)

    @staticmethod
    def calmar_ratio(
        returns: list[float],
        periods_per_year: int = 252,
    ) -> float:
        """
        Calmar Ratio — annualized return / max drawdown.

        Args:
            returns: List of period returns.
            periods_per_year: Trading periods per year.

        Returns:
            Calmar ratio (higher is better).
        """
        if not returns:
            return 0.0
        ann_ret = sum(returns) / len(returns) * periods_per_year
        dd_info = RiskMetrics.max_drawdown(returns)
        if dd_info.max_drawdown == 0:
            return float('inf') if ann_ret > 0 else 0.0
        return ann_ret / abs(dd_info.max_drawdown)

    @staticmethod
    def win_rate(trade_pnls: list[float]) -> float:
        """
        Win rate — fraction of profitable trades.

        Args:
            trade_pnls: List of trade P&L values.

        Returns:
            Win rate (0-1).
        """
        if not trade_pnls:
            return 0.0
        wins = sum(1 for t in trade_pnls if t > 0)
        return wins / len(trade_pnls)

    @staticmethod
    def profit_factor(trade_pnls: list[float]) -> float:
        """
        Profit Factor — gross profits / gross losses.

        Args:
            trade_pnls: List of trade P&L values.

        Returns:
            Profit factor (>1 is profitable).
        """
        gross_profit = sum(t for t in trade_pnls if t > 0)
        gross_loss = abs(sum(t for t in trade_pnls if t < 0))
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @staticmethod
    def risk_reward_ratio(trade_pnls: list[float]) -> float:
        """
        Risk-Reward Ratio — average win / average loss.

        Args:
            trade_pnls: List of trade P&L values.

        Returns:
            Risk-reward ratio (higher is better).
        """
        wins = [t for t in trade_pnls if t > 0]
        losses = [t for t in trade_pnls if t < 0]
        if not wins or not losses:
            return 0.0
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        if avg_loss == 0:
            return float('inf')
        return avg_win / avg_loss

    @staticmethod
    def skewness(returns: list[float]) -> float:
        """Return distribution skewness."""
        n = len(returns)
        if n < 3:
            return 0.0
        mean = sum(returns) / n
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / (n - 1))
        if std == 0:
            return 0.0
        return (n / ((n - 1) * (n - 2))) * sum(((r - mean) / std) ** 3 for r in returns)

    @staticmethod
    def kurtosis(returns: list[float]) -> float:
        """Excess kurtosis of return distribution."""
        n = len(returns)
        if n < 4:
            return 0.0
        mean = sum(returns) / n
        std = math.sqrt(sum((r - mean) ** 2 for r in returns) / (n - 1))
        if std == 0:
            return 0.0
        m4 = sum(((r - mean) / std) ** 4 for r in returns) / n
        return m4 - 3.0

    @staticmethod
    def full_report(
        returns: list[float],
        trade_pnls: Optional[list[float]] = None,
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> RiskReport:
        """
        Generate a complete risk report.

        Args:
            returns: List of period returns (e.g. daily).
            trade_pnls: Optional list of individual trade P&L values.
            risk_free_rate: Annualized risk-free rate.
            periods_per_year: Periods per year.

        Returns:
            RiskReport dataclass with all metrics.
        """
        if not returns:
            return RiskReport(
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            )

        # Equity curve
        equity = 1.0
        for r in returns:
            equity *= (1 + r)
        total_return = equity - 1.0

        mean_ret = sum(returns) / len(returns)
        ann_ret = mean_ret * periods_per_year
        ann_vol = math.sqrt(
            sum((r - mean_ret) ** 2 for r in returns) / max(len(returns) - 1, 1)
        ) * math.sqrt(periods_per_year)

        dd_info = RiskMetrics.max_drawdown(returns)
        trades = trade_pnls or []

        return RiskReport(
            total_return=total_return,
            annualized_return=ann_ret,
            annualized_volatility=ann_vol,
            sharpe_ratio=RiskMetrics.sharpe_ratio(returns, risk_free_rate, periods_per_year),
            sortino_ratio=RiskMetrics.sortino_ratio(returns, risk_free_rate, periods_per_year),
            calmar_ratio=RiskMetrics.calmar_ratio(returns, periods_per_year),
            max_drawdown=dd_info.max_drawdown,
            max_drawdown_duration=dd_info.max_drawdown_duration,
            var_95=RiskMetrics.value_at_risk(returns, 0.95),
            cvar_95=RiskMetrics.conditional_var(returns, 0.95),
            var_99=RiskMetrics.value_at_risk(returns, 0.99),
            cvar_99=RiskMetrics.conditional_var(returns, 0.99),
            win_rate=RiskMetrics.win_rate(trades),
            profit_factor=RiskMetrics.profit_factor(trades),
            risk_reward_ratio=RiskMetrics.risk_reward_ratio(trades),
            num_trades=len(trades),
            skewness=RiskMetrics.skewness(returns),
            kurtosis=RiskMetrics.kurtosis(returns),
        )
