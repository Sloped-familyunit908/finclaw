"""
FinClaw - Strategy Backtesting Engines
======================================
Standalone strategy implementations for the backtest CLI.

Each strategy class follows the same interface:
    async def run(asset, strategy_name, price_history, ...) -> BacktestResult

Strategies:
- MACDStrategy: MACD crossover (buy when MACD > signal, sell when MACD < signal)
- BollingerStrategy: Bollinger Bands mean reversion (buy at lower band, sell at upper)
- MomentumStrategy: Breakout momentum (buy above N-day high, sell below N-day low)
"""

import math
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from agents.backtester import BacktestResult, Trade


def _std(values):
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _ema(prices: list[float], period: int) -> list[float]:
    """Compute EMA over a list of floats."""
    alpha = 2.0 / (period + 1)
    out = [prices[0]]
    for i in range(1, len(prices)):
        out.append(alpha * prices[i] + (1 - alpha) * out[-1])
    return out


def _sma(prices: list[float], period: int) -> list[float]:
    """Compute SMA over a list of floats. NaN-fill for indices < period-1."""
    out = [float('nan')] * len(prices)
    if len(prices) < period:
        return out
    s = sum(prices[:period])
    out[period - 1] = s / period
    for i in range(period, len(prices)):
        s += prices[i] - prices[i - period]
        out[i] = s / period
    return out


def _macd(prices: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9):
    """MACD -> (macd_line, signal_line, histogram) as lists."""
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, histogram


def _bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0):
    """Bollinger Bands -> (upper, middle, lower) as lists."""
    n = len(prices)
    middle = _sma(prices, period)
    upper = [float('nan')] * n
    lower = [float('nan')] * n
    for i in range(period - 1, n):
        window = prices[i - period + 1: i + 1]
        m = sum(window) / period
        std = math.sqrt(sum((x - m) ** 2 for x in window) / period)  # population std
        upper[i] = middle[i] + num_std * std
        lower[i] = middle[i] - num_std * std
    return upper, middle, lower


class _BaseStrategyBacktester:
    """Shared backtesting scaffold for all strategies."""

    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.0005,
                 position_size_pct: float = 0.95):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.position_size_pct = position_size_pct

    # Subclasses must implement warmup_period and generate_signal
    @property
    def warmup_period(self) -> int:
        raise NotImplementedError

    def generate_signal(self, prices: list[float], i: int) -> str:
        """Return 'buy', 'sell', or 'hold' for bar index i."""
        raise NotImplementedError

    async def run(self, asset: str, strategy_name: str,
                  price_history: list[dict],
                  arena=None, agents=None,
                  decision_interval: int = 1) -> BacktestResult:

        if not price_history or len(price_history) < self.warmup_period + 1:
            raise ValueError(f"Need at least {self.warmup_period + 1} data points")

        prices_arr = [bar["price"] for bar in price_history]

        capital = self.initial_capital
        position_qty = 0.0
        entry_price = 0.0
        entry_time = None
        trades: list[Trade] = []
        equity_curve = [capital]
        daily_returns = []

        warmup = self.warmup_period
        total = len(price_history)

        for i in range(warmup, total):
            price = price_history[i]["price"]
            date = price_history[i].get("date", datetime.now())
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date)
                except Exception:
                    date = datetime.now()

            # Update equity
            current_equity = capital + position_qty * price
            equity_curve.append(current_equity)
            if len(equity_curve) > 2 and equity_curve[-2] > 0:
                daily_returns.append((current_equity - equity_curve[-2]) / equity_curve[-2])

            if (i - warmup) % decision_interval != 0:
                continue

            signal = self.generate_signal(prices_arr, i)

            if position_qty == 0 and signal == "buy":
                trade_capital = capital * self.position_size_pct
                if trade_capital < 1.0:
                    continue
                effective_price = price * (1 + self.slippage_pct)
                commission = trade_capital * self.commission_pct
                position_qty = (trade_capital - commission) / effective_price
                capital -= trade_capital
                entry_price = effective_price
                entry_time = date

            elif position_qty > 0 and signal == "sell":
                effective_price = price * (1 - self.slippage_pct)
                proceeds = position_qty * effective_price
                commission = proceeds * self.commission_pct
                capital += proceeds - commission

                pnl = (effective_price - entry_price) * position_qty
                pnl_pct = (effective_price / entry_price) - 1 if entry_price > 0 else 0

                trades.append(Trade(
                    asset=asset, side="long",
                    entry_price=entry_price, exit_price=effective_price,
                    entry_time=entry_time if isinstance(entry_time, datetime) else datetime.now(),
                    exit_time=date if isinstance(date, datetime) else datetime.now(),
                    quantity=position_qty, pnl=pnl, pnl_pct=pnl_pct,
                    signal_source=strategy_name,
                    debate_confidence=0.6,
                ))
                position_qty = 0.0
                entry_price = 0.0

        # Close any open position at end
        if position_qty > 0:
            final_price = price_history[-1]["price"]
            effective_price = final_price * (1 - self.slippage_pct)
            proceeds = position_qty * effective_price
            commission = proceeds * self.commission_pct
            capital += proceeds - commission

            pnl = (effective_price - entry_price) * position_qty
            pnl_pct = (effective_price / entry_price) - 1 if entry_price > 0 else 0

            final_date = price_history[-1].get("date", datetime.now())
            if isinstance(final_date, str):
                try:
                    final_date = datetime.fromisoformat(final_date)
                except Exception:
                    final_date = datetime.now()

            trades.append(Trade(
                asset=asset, side="long",
                entry_price=entry_price, exit_price=effective_price,
                entry_time=entry_time if isinstance(entry_time, datetime) else datetime.now(),
                exit_time=final_date if isinstance(final_date, datetime) else datetime.now(),
                quantity=position_qty, pnl=pnl, pnl_pct=pnl_pct,
                signal_source="close", debate_confidence=0.5,
            ))
            position_qty = 0.0

        return self._build_result(
            strategy_name, asset, price_history, warmup,
            capital, trades, equity_curve, daily_returns
        )

    def _build_result(self, strategy_name, asset, price_history, warmup,
                      final_capital, trades, equity_curve, daily_returns):
        total_return = (final_capital / self.initial_capital) - 1

        start_price = price_history[warmup]["price"]
        end_price = price_history[-1]["price"]
        bh_return = (end_price / start_price) - 1

        days = max(len(price_history) - warmup, 1)
        years = max(days / 365, 0.01)
        ann_return = (1 + total_return) ** (1 / years) - 1 if total_return > -1 else -1
        alpha = total_return - bh_return

        if daily_returns and len(daily_returns) > 1:
            vol = _std(daily_returns) * math.sqrt(365)
            down = [r for r in daily_returns if r < 0]
            down_dev = _std(down) * math.sqrt(365) if len(down) > 1 else 0.001
            avg_r = sum(daily_returns) / len(daily_returns) * 365
            sharpe = (avg_r - 0.05) / max(vol, 0.001)
            sortino = (avg_r - 0.05) / max(down_dev, 0.001)

            peak = equity_curve[0]
            max_dd = 0
            dd_curve = []
            for eq in equity_curve:
                peak = max(peak, eq)
                dd = (eq - peak) / peak if peak > 0 else 0
                dd_curve.append(dd)
                max_dd = min(max_dd, dd)
            calmar = ann_return / max(abs(max_dd), 0.001) if max_dd != 0 else 0

            s = sorted(daily_returns)
            vi = max(int(len(s) * 0.05), 1)
            var_95 = s[vi - 1] if s else 0
            cvar_95 = sum(s[:vi]) / vi if s else 0

            excess = [r - bh_return / max(days, 1) for r in daily_returns]
            te = _std(excess) * math.sqrt(365) if len(excess) > 1 else 0.001
            info_ratio = alpha / max(te * years, 0.001)
        else:
            vol = down_dev = sharpe = sortino = calmar = 0
            max_dd = 0
            dd_curve = [0]
            var_95 = cvar_95 = info_ratio = 0

        max_dd_dur = 0
        dd_start = 0
        in_dd = False
        pk = equity_curve[0] if equity_curve else 0
        for idx, eq in enumerate(equity_curve):
            if eq >= pk:
                pk = eq
                if in_dd:
                    max_dd_dur = max(max_dd_dur, idx - dd_start)
                    in_dd = False
            elif not in_dd:
                dd_start = idx
                in_dd = True

        win = [t for t in trades if t.pnl > 0]
        lose = [t for t in trades if t.pnl <= 0]
        wr = len(win) / max(len(trades), 1)
        avg_win = sum(t.pnl_pct for t in win) / max(len(win), 1)
        avg_loss = sum(t.pnl_pct for t in lose) / max(len(lose), 1)
        gp = sum(t.pnl for t in win)
        gl = abs(sum(t.pnl for t in lose))
        pf = gp / max(gl, 0.01)
        avg_dur = 0
        if trades:
            durs = [(t.exit_time - t.entry_time).total_seconds() / 3600
                    for t in trades
                    if isinstance(t.entry_time, datetime) and isinstance(t.exit_time, datetime)]
            avg_dur = sum(durs) / max(len(durs), 1)

        confs = [t.debate_confidence for t in trades] or [0]

        return BacktestResult(
            strategy_name=strategy_name, asset=asset,
            start_date=price_history[warmup].get("date", datetime.now()) if isinstance(
                price_history[warmup].get("date"), datetime) else datetime.now(),
            end_date=price_history[-1].get("date", datetime.now()) if isinstance(
                price_history[-1].get("date"), datetime) else datetime.now(),
            total_return=total_return, annualized_return=ann_return,
            benchmark_return=bh_return, alpha=alpha,
            sharpe_ratio=sharpe, sortino_ratio=sortino, calmar_ratio=calmar,
            max_drawdown=max_dd, max_drawdown_duration_days=max_dd_dur,
            volatility=vol, downside_deviation=down_dev,
            information_ratio=info_ratio, cvar_95=cvar_95, var_95=var_95,
            total_trades=len(trades), winning_trades=len(win), losing_trades=len(lose),
            win_rate=wr, avg_win=avg_win, avg_loss=avg_loss,
            profit_factor=pf, avg_trade_duration_hours=avg_dur,
            avg_debate_confidence=sum(confs) / len(confs),
            high_confidence_win_rate=0, low_confidence_win_rate=0,
            confidence_correlation=0.0,
            debate_rounds_avg=1.0, consensus_rate=1.0,
            equity_curve=equity_curve, drawdown_curve=dd_curve,
            daily_returns=daily_returns, trades=trades,
        )


class MACDStrategy(_BaseStrategyBacktester):
    """
    MACD Crossover Strategy.

    Buy when MACD line crosses above the signal line.
    Sell when MACD line crosses below the signal line.
    """

    def __init__(self, initial_capital: float = 10000.0,
                 fast: int = 12, slow: int = 26, signal_period: int = 9,
                 **kwargs):
        super().__init__(initial_capital=initial_capital, **kwargs)
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self._macd_cache = None
        self._cache_len = 0

    @property
    def warmup_period(self) -> int:
        return self.slow + self.signal_period

    def generate_signal(self, prices: list[float], i: int) -> str:
        if i < self.warmup_period:
            return "hold"

        # Recompute MACD if prices changed (full-history approach)
        if self._cache_len != len(prices):
            self._macd_cache = _macd(prices, self.fast, self.slow, self.signal_period)
            self._cache_len = len(prices)

        macd_line, signal_line, histogram = self._macd_cache

        # Crossover detection
        if i < 1:
            return "hold"

        prev_hist = histogram[i - 1]
        curr_hist = histogram[i]

        # Buy: histogram crosses from negative to positive (MACD crosses above signal)
        if prev_hist <= 0 and curr_hist > 0:
            return "buy"
        # Sell: histogram crosses from positive to negative (MACD crosses below signal)
        elif prev_hist >= 0 and curr_hist < 0:
            return "sell"

        return "hold"


class BollingerStrategy(_BaseStrategyBacktester):
    """
    Bollinger Bands Mean Reversion Strategy.

    Buy when price touches or drops below the lower band.
    Sell when price touches or exceeds the upper band.
    """

    def __init__(self, initial_capital: float = 10000.0,
                 period: int = 20, num_std: float = 2.0,
                 **kwargs):
        super().__init__(initial_capital=initial_capital, **kwargs)
        self.period = period
        self.num_std = num_std
        self._bb_cache = None
        self._cache_len = 0

    @property
    def warmup_period(self) -> int:
        return self.period

    def generate_signal(self, prices: list[float], i: int) -> str:
        if i < self.warmup_period:
            return "hold"

        # Recompute Bollinger Bands if prices changed
        if self._cache_len != len(prices):
            self._bb_cache = _bollinger_bands(prices, self.period, self.num_std)
            self._cache_len = len(prices)

        upper, middle, lower = self._bb_cache
        price = prices[i]

        if math.isnan(upper[i]) or math.isnan(lower[i]):
            return "hold"

        # Buy: price at or below lower band (oversold / mean reversion entry)
        if price <= lower[i]:
            return "buy"
        # Sell: price at or above upper band (overbought / mean reversion exit)
        elif price >= upper[i]:
            return "sell"

        return "hold"


class MomentumStrategy(_BaseStrategyBacktester):
    """
    Momentum / Breakout Strategy.

    Buy when price exceeds the highest high of the last N days.
    Sell when price drops below the lowest low of the last N days.
    """

    def __init__(self, initial_capital: float = 10000.0,
                 lookback: int = 20,
                 **kwargs):
        super().__init__(initial_capital=initial_capital, **kwargs)
        self.lookback = lookback

    @property
    def warmup_period(self) -> int:
        return self.lookback

    def generate_signal(self, prices: list[float], i: int) -> str:
        if i < self.lookback:
            return "hold"

        window = prices[i - self.lookback: i]  # last N bars (not including current)
        highest = max(window)
        lowest = min(window)
        price = prices[i]

        # Buy: breakout above N-day high
        if price > highest:
            return "buy"
        # Sell: breakdown below N-day low
        elif price < lowest:
            return "sell"

        return "hold"


# Registry for CLI dispatch
STRATEGY_MAP = {
    "macd": MACDStrategy,
    "bollinger": BollingerStrategy,
    "momentum": MomentumStrategy,
}
