"""
FinClaw - Position Sizing Calculator
Multiple position sizing methods for risk management.
"""

from __future__ import annotations

import math
from typing import Optional


class PositionSizer:
    """
    Collection of position sizing algorithms.

    All methods are static — no state needed.
    Use the method that matches your risk management style.
    """

    @staticmethod
    def fixed_dollar(capital: float, risk_per_trade: float) -> float:
        """
        Fixed dollar amount position sizing.

        Args:
            capital: Total available capital
            risk_per_trade: Dollar amount to risk per trade

        Returns:
            Position size as fraction of capital (0-1)
        """
        if capital <= 0 or risk_per_trade <= 0:
            return 0.0
        return min(risk_per_trade / capital, 1.0)

    @staticmethod
    def percent_risk(
        capital: float,
        entry: float,
        stop: float,
        risk_pct: float = 0.02,
    ) -> int:
        """
        Calculate number of shares based on percent risk model.

        Risk a fixed percentage of capital. Position size determined by
        distance to stop loss.

        Args:
            capital: Total capital
            entry: Entry price
            stop: Stop-loss price
            risk_pct: Percentage of capital to risk (default 2%)

        Returns:
            Number of shares (integer, rounded down)
        """
        if capital <= 0 or entry <= 0 or risk_pct <= 0:
            return 0
        risk_amount = capital * risk_pct
        stop_distance = abs(entry - stop)
        if stop_distance < 1e-10:
            return 0
        shares = risk_amount / stop_distance
        return int(shares)

    @staticmethod
    def kelly(
        win_rate: float,
        win_loss_ratio: float,
        fraction: float = 0.5,
    ) -> float:
        """
        Kelly Criterion position sizing.

        f* = (bp - q) / b where b = win/loss ratio, p = win_rate, q = 1-p
        Returns fractional Kelly (default half-Kelly for safety).

        Args:
            win_rate: Probability of winning (0-1)
            win_loss_ratio: Average win / average loss
            fraction: Kelly fraction (0.5 = half-Kelly)

        Returns:
            Fraction of capital to bet (0-1, clamped)
        """
        if win_rate <= 0 or win_rate >= 1 or win_loss_ratio <= 0:
            return 0.0

        b = win_loss_ratio
        p = win_rate
        q = 1 - p
        kelly_full = (b * p - q) / b

        if kelly_full <= 0:
            return 0.0

        return min(kelly_full * fraction, 1.0)

    @staticmethod
    def volatility_based(
        capital: float,
        price: float,
        atr: float,
        risk_pct: float = 0.02,
    ) -> int:
        """
        Volatility-based position sizing using ATR.

        Size inversely proportional to volatility — trade smaller
        when volatility is high.

        Args:
            capital: Total capital
            price: Current price
            atr: Average True Range (dollar value)
            risk_pct: Percentage of capital to risk

        Returns:
            Number of shares (integer)
        """
        if capital <= 0 or price <= 0 or atr <= 0 or risk_pct <= 0:
            return 0
        risk_amount = capital * risk_pct
        shares = risk_amount / atr
        # Cap at what capital can buy
        max_shares = capital / price
        return int(min(shares, max_shares))

    @staticmethod
    def optimal_f(trades: list[float]) -> float:
        """
        Optimal f — Ralph Vince's method.

        Finds the fraction that maximizes the geometric growth rate
        based on historical trade results.

        Args:
            trades: List of trade P&L values (positive = win, negative = loss)

        Returns:
            Optimal fraction (0-1)
        """
        if not trades or all(t >= 0 for t in trades):
            return 0.0

        worst_loss = abs(min(trades))
        if worst_loss == 0:
            return 0.0

        best_f = 0.0
        best_twrr = 0.0

        # Search f from 0.01 to 1.0 in steps of 0.01
        for f_int in range(1, 101):
            f = f_int / 100.0
            twrr = 1.0
            for t in trades:
                hpr = 1.0 + f * (-t / worst_loss) if t < 0 else 1.0 + f * (t / worst_loss)
                if hpr <= 0:
                    twrr = 0.0
                    break
                twrr *= hpr

            if twrr > best_twrr:
                best_twrr = twrr
                best_f = f

        return best_f

    @staticmethod
    def equal_weight(n_positions: int) -> float:
        """
        Equal weight allocation across N positions.

        Args:
            n_positions: Number of positions

        Returns:
            Weight per position (0-1)
        """
        if n_positions <= 0:
            return 0.0
        return 1.0 / n_positions

    @staticmethod
    def risk_parity(volatilities: list[float]) -> list[float]:
        """
        Risk parity allocation — weight inversely proportional to volatility.

        Each position contributes equal risk to the portfolio.

        Args:
            volatilities: List of annualized volatilities for each asset.

        Returns:
            List of weights (0-1) summing to 1.0.
        """
        if not volatilities or all(v <= 0 for v in volatilities):
            return [0.0] * len(volatilities) if volatilities else []
        inv_vols = [1.0 / max(v, 1e-10) for v in volatilities]
        total = sum(inv_vols)
        return [iv / total for iv in inv_vols]
