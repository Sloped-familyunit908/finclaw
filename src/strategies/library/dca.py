"""
Dollar Cost Averaging (DCA)
===========================
Smart DCA with optional RSI-based timing enhancement.

Parameters:
    amount_per_period: Amount to invest each period (default: 100).
    period: Investment frequency — daily, weekly, biweekly, monthly (default: weekly).
    smart_timing: Use RSI to increase buys when oversold (default: True).
    rsi_period: RSI lookback (default: 14).
    rsi_boost_threshold: Buy extra when RSI below this (default: 30).
    boost_multiplier: Extra multiplier when RSI is low (default: 1.5).

Usage:
    strategy = DCAStrategy(amount_per_period=200, period='weekly', smart_timing=True)
    signals = strategy.generate_signals(ohlcv_data)
    result = strategy.backtest(ohlcv_data)
"""

from __future__ import annotations
from typing import Any
from .base import Strategy, StrategySignal, StrategyMeta, rsi as calc_rsi


class DCAStrategy(Strategy):
    """Dollar Cost Averaging with optional smart timing (RSI enhancement)."""

    PERIOD_BARS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}

    def __init__(
        self,
        amount_per_period: float = 100.0,
        period: str = "weekly",
        smart_timing: bool = True,
        rsi_period: int = 14,
        rsi_boost_threshold: float = 30.0,
        boost_multiplier: float = 1.5,
        initial_capital: float = 10_000,
    ):
        super().__init__(initial_capital=initial_capital)
        if amount_per_period <= 0:
            raise ValueError("amount_per_period must be positive")
        if period not in self.PERIOD_BARS:
            raise ValueError(f"period must be one of {list(self.PERIOD_BARS.keys())}")
        self.amount_per_period = amount_per_period
        self.period = period
        self.smart_timing = smart_timing
        self.rsi_period = rsi_period
        self.rsi_boost_threshold = rsi_boost_threshold
        self.boost_multiplier = boost_multiplier
        self._interval = self.PERIOD_BARS[period]

    @classmethod
    def meta(cls) -> StrategyMeta:
        return StrategyMeta(
            name="Dollar Cost Averaging",
            slug="dca",
            category="crypto",
            description="Smart DCA with optional RSI-based timing. Buy more when oversold.",
            parameters={
                "amount_per_period": "Investment per period (default: 100)",
                "period": "Frequency: daily/weekly/biweekly/monthly (default: weekly)",
                "smart_timing": "Enable RSI-based boost (default: True)",
                "rsi_boost_threshold": "RSI threshold for extra buying (default: 30)",
                "boost_multiplier": "Extra buy multiplier when RSI low (default: 1.5)",
            },
            usage_example="finclaw strategy backtest dca --symbol BTCUSDT --start 2024-01-01",
        )

    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        signals: list[StrategySignal] = []
        closes = [bar["close"] for bar in data]

        for i, bar in enumerate(data):
            if i % self._interval != 0:
                signals.append(StrategySignal("hold", 0.0, price=bar["close"], reason="waiting for DCA period"))
                continue

            amount = self.amount_per_period
            rsi_val = None

            if self.smart_timing and i >= self.rsi_period + 1:
                rsi_val = calc_rsi(closes[: i + 1], self.rsi_period)
                if rsi_val is not None and rsi_val < self.rsi_boost_threshold:
                    amount *= self.boost_multiplier

            signals.append(StrategySignal(
                "buy", 0.6, price=bar["close"], quantity=amount / bar["close"],
                reason=f"DCA buy #{i // self._interval}" + (f" (RSI={rsi_val:.1f}, boosted)" if rsi_val and rsi_val < self.rsi_boost_threshold else ""),
                metadata={"amount": amount, "rsi": rsi_val},
            ))

        return signals

    def backtest(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """DCA-specific backtest: accumulate tokens over time."""
        signals = self.generate_signals(data)
        total_invested = 0.0
        total_tokens = 0.0
        buys = 0

        for i, (bar, sig) in enumerate(zip(data, signals)):
            if sig.action == "buy":
                amount = sig.metadata.get("amount", self.amount_per_period)
                tokens = amount / bar["close"]
                total_invested += amount
                total_tokens += tokens
                buys += 1

        avg_price = total_invested / total_tokens if total_tokens > 0 else 0
        final_price = data[-1]["close"] if data else 0
        final_value = total_tokens * final_price
        pnl_pct = ((final_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

        return {
            "total_invested": round(total_invested, 2),
            "total_tokens": round(total_tokens, 8),
            "avg_price": round(avg_price, 2),
            "final_price": final_price,
            "final_value": round(final_value, 2),
            "total_return": round(pnl_pct, 2),
            "num_trades": buys,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 100.0 if pnl_pct > 0 else 0.0,
            "final_equity": round(final_value, 2),
            "equity_curve": [],
        }
