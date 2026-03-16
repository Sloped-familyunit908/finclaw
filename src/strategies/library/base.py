"""
Base Strategy Class
===================
All built-in strategies extend this base class.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StrategySignal:
    """A trading signal produced by a strategy."""
    action: str  # "buy", "sell", "hold", "long_a_short_b", "close"
    confidence: float  # 0.0 - 1.0
    price: float = 0.0
    quantity: float = 0.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyMeta:
    """Metadata describing a strategy."""
    name: str
    slug: str
    category: str  # "crypto", "stock", "universal"
    description: str
    parameters: dict[str, str]
    usage_example: str


class Strategy(ABC):
    """Abstract base for all FinClaw strategies.

    Subclasses must implement:
        - meta() -> StrategyMeta (classmethod)
        - generate_signals(data) -> list[StrategySignal]

    Parameters:
        initial_capital: Starting capital for backtesting.
    """

    def __init__(self, initial_capital: float = 10_000.0, **kwargs: Any):
        self.initial_capital = initial_capital
        self.positions: list[dict[str, Any]] = []
        self.trades: list[dict[str, Any]] = []

    @classmethod
    @abstractmethod
    def meta(cls) -> StrategyMeta:
        """Return strategy metadata."""
        ...

    @abstractmethod
    def generate_signals(self, data: list[dict[str, Any]]) -> list[StrategySignal]:
        """Generate trading signals from OHLCV data.

        Args:
            data: List of dicts with keys: open, high, low, close, volume.
                  May include additional keys depending on strategy.

        Returns:
            List of StrategySignal, one per data bar.
        """
        ...

    def backtest(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Run a simple vectorized backtest.

        Returns dict with: total_return, sharpe_ratio, max_drawdown, win_rate, num_trades, equity_curve.
        """
        signals = self.generate_signals(data)
        capital = self.initial_capital
        position = 0.0
        entry_price = 0.0
        equity_curve: list[float] = []
        trades: list[dict[str, Any]] = []
        wins = 0

        for i, (bar, sig) in enumerate(zip(data, signals)):
            price = bar["close"]
            if sig.action == "buy" and position == 0:
                position = capital / price
                entry_price = price
                capital = 0.0
            elif sig.action == "sell" and position > 0:
                capital = position * price
                pnl = (price - entry_price) / entry_price
                trades.append({"entry": entry_price, "exit": price, "pnl_pct": pnl})
                if pnl > 0:
                    wins += 1
                position = 0.0
                entry_price = 0.0

            equity = capital + position * price
            equity_curve.append(equity)

        # Close open position at end
        if position > 0:
            final_price = data[-1]["close"]
            capital = position * final_price
            pnl = (final_price - entry_price) / entry_price
            trades.append({"entry": entry_price, "exit": final_price, "pnl_pct": pnl})
            if pnl > 0:
                wins += 1
            position = 0.0

        final_equity = equity_curve[-1] if equity_curve else self.initial_capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        # Max drawdown
        peak = self.initial_capital
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplified, annualized daily)
        if len(equity_curve) > 1:
            returns = []
            for j in range(1, len(equity_curve)):
                r = (equity_curve[j] - equity_curve[j - 1]) / equity_curve[j - 1] if equity_curve[j - 1] > 0 else 0
                returns.append(r)
            avg_r = sum(returns) / len(returns) if returns else 0
            std_r = math.sqrt(sum((r - avg_r) ** 2 for r in returns) / len(returns)) if returns else 0
            sharpe = (avg_r / std_r * math.sqrt(252)) if std_r > 0 else 0
        else:
            sharpe = 0.0

        num_trades = len(trades)
        win_rate = (wins / num_trades * 100) if num_trades > 0 else 0

        return {
            "total_return": round(total_return * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd * 100, 2),
            "win_rate": round(win_rate, 2),
            "num_trades": num_trades,
            "final_equity": round(final_equity, 2),
            "equity_curve": equity_curve,
        }


# ── Helpers ──────────────────────────────────────────────────────────

def sma(values: list[float], period: int) -> Optional[float]:
    """Simple moving average of last *period* values."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema(values: list[float], period: int) -> Optional[float]:
    """Exponential moving average."""
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = v * k + result * (1 - k)
    return result


def rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0) -> Optional[tuple[float, float, float]]:
    """Return (upper, middle, lower) Bollinger Bands."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    mid = sum(window) / period
    variance = sum((p - mid) ** 2 for p in window) / period
    std = math.sqrt(variance)
    return (mid + num_std * std, mid, mid - num_std * std)


def adx(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> Optional[float]:
    """Average Directional Index."""
    if len(highs) < period + 2:
        return None
    plus_dm_list, minus_dm_list, tr_list = [], [], []
    for i in range(-period - 1, 0):
        high_diff = highs[i] - highs[i - 1]
        low_diff = lows[i - 1] - lows[i]
        plus_dm = max(high_diff, 0) if high_diff > low_diff else 0
        minus_dm = max(low_diff, 0) if low_diff > high_diff else 0
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)

    atr = sum(tr_list[:period]) / period
    plus_di = (sum(plus_dm_list[:period]) / period) / atr * 100 if atr > 0 else 0
    minus_di = (sum(minus_dm_list[:period]) / period) / atr * 100 if atr > 0 else 0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    return dx


def donchian_channel(highs: list[float], lows: list[float], period: int = 20) -> Optional[tuple[float, float, float]]:
    """Return (upper, middle, lower) Donchian Channel."""
    if len(highs) < period or len(lows) < period:
        return None
    upper = max(highs[-period:])
    lower = min(lows[-period:])
    middle = (upper + lower) / 2
    return (upper, middle, lower)
