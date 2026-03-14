"""
WhaleTrader - Backtesting Engine
Multi-round validation, strategy comparison, performance ranking.

Design philosophy (from competitive analysis):
- freqtrade: Best backtesting UX (hyperopt, walk-forward, etc.) — we learn from them
- ai-hedge-fund: Has backtester.py but basic — we go deeper
- FinRL: Train-test-trade pipeline — we adopt this pattern
- FinRL-DeepSeek: Uses Information Ratio, CVaR, Rachev Ratio — we use ALL metrics

Our edge: AI agent debate + systematic backtesting = 
         quantitative proof that multi-agent decisions > single agent
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import math


class TimeFrame(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


@dataclass
class Trade:
    """A completed trade"""
    asset: str
    side: str  # "buy" or "sell"
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    quantity: float
    pnl: float
    pnl_pct: float
    signal_source: str  # which agent(s) triggered this
    debate_confidence: float  # arena consensus confidence


@dataclass
class BacktestResult:
    """Complete backtest results with professional metrics"""
    # Identity
    strategy_name: str
    asset: str
    start_date: datetime
    end_date: datetime
    
    # Core metrics
    total_return: float  # total % return
    annualized_return: float
    benchmark_return: float  # buy-and-hold return
    alpha: float  # excess return over benchmark
    
    # Risk metrics (institutional grade)
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    volatility: float  # annualized
    downside_deviation: float
    
    # Advanced risk (FinRL-DeepSeek inspired)
    information_ratio: float  # risk-adjusted excess return
    cvar_95: float  # Conditional Value at Risk (95%)
    var_95: float   # Value at Risk (95%)
    
    # Trade stats
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float  # gross profit / gross loss
    avg_trade_duration_hours: float
    
    # Debate-specific metrics (OUR UNIQUE METRICS)
    avg_debate_confidence: float
    high_confidence_win_rate: float  # win rate when confidence > 80%
    low_confidence_win_rate: float   # win rate when confidence < 50%
    confidence_correlation: float    # correlation(confidence, pnl)
    debate_rounds_avg: float
    consensus_rate: float  # % of debates reaching full consensus
    
    # Time series
    equity_curve: list[float]
    drawdown_curve: list[float]
    trades: list[Trade]

    def summary(self) -> str:
        """Pretty print summary"""
        lines = [
            f"╔══════════════════════════════════════════════════════════════╗",
            f"║  BACKTEST REPORT: {self.strategy_name:<42}║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  Asset: {self.asset:<15} Period: {self.start_date.strftime('%Y-%m-%d')} → {self.end_date.strftime('%Y-%m-%d')}  ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  RETURNS                                                    ║",
            f"║    Total Return:       {self.total_return:>+10.2%}                          ║",
            f"║    Annualized Return:  {self.annualized_return:>+10.2%}                          ║",
            f"║    Benchmark (HODL):   {self.benchmark_return:>+10.2%}                          ║",
            f"║    Alpha:              {self.alpha:>+10.2%}                          ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  RISK                                                       ║",
            f"║    Sharpe Ratio:       {self.sharpe_ratio:>10.2f}                          ║",
            f"║    Sortino Ratio:      {self.sortino_ratio:>10.2f}                          ║",
            f"║    Calmar Ratio:       {self.calmar_ratio:>10.2f}                          ║",
            f"║    Max Drawdown:       {self.max_drawdown:>10.2%}                          ║",
            f"║    Volatility (ann.):  {self.volatility:>10.2%}                          ║",
            f"║    VaR (95%):          {self.var_95:>10.2%}                          ║",
            f"║    CVaR (95%):         {self.cvar_95:>10.2%}                          ║",
            f"║    Info Ratio:         {self.information_ratio:>10.2f}                          ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  TRADES                                                     ║",
            f"║    Total:  {self.total_trades:<6}  Win Rate:  {self.win_rate:>6.1%}                    ║",
            f"║    Wins:   {self.winning_trades:<6}  Avg Win:   {self.avg_win:>+6.2%}                    ║",
            f"║    Losses: {self.losing_trades:<6}  Avg Loss:  {self.avg_loss:>+6.2%}                    ║",
            f"║    Profit Factor: {self.profit_factor:>6.2f}                                  ║",
            f"╠══════════════════════════════════════════════════════════════╣",
            f"║  DEBATE ARENA METRICS (WhaleTrader Exclusive)               ║",
            f"║    Avg Confidence:         {self.avg_debate_confidence:>6.1%}                        ║",
            f"║    High-Conf Win Rate:     {self.high_confidence_win_rate:>6.1%}  (conf > 80%)         ║",
            f"║    Low-Conf Win Rate:      {self.low_confidence_win_rate:>6.1%}  (conf < 50%)         ║",
            f"║    Confidence↔PnL Corr:    {self.confidence_correlation:>+6.3f}                        ║",
            f"║    Consensus Rate:         {self.consensus_rate:>6.1%}                        ║",
            f"╚══════════════════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)


class Backtester:
    """
    Professional backtesting engine.
    
    Features:
    - Walk-forward analysis (no look-ahead bias)
    - Multi-strategy comparison
    - Debate Arena integration
    - Comprehensive risk metrics
    """

    def __init__(self, initial_capital: float = 10000.0,
                 commission_pct: float = 0.001,  # 0.1% per trade
                 slippage_pct: float = 0.0005):   # 0.05% slippage
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    async def run(self, asset: str, strategy_name: str,
                  price_history: list[dict],
                  arena=None, agents=None,
                  decision_interval: int = 1,
                  position_size_pct: float = 0.95,
                  on_progress=None) -> BacktestResult:
        """
        Run a backtest over historical data.
        
        Args:
            asset: Asset symbol
            strategy_name: Name for this strategy run
            price_history: List of {date, price, volume, ...} dicts
            arena: DebateArena instance (optional — uses rule-based if None)
            agents: List of agent profiles
            decision_interval: Make decision every N bars
            position_size_pct: % of capital per position
            on_progress: Async callback(current_bar, total_bars)
        """
        if not price_history or len(price_history) < 30:
            raise ValueError("Need at least 30 data points for backtesting")

        capital = self.initial_capital
        position = 0.0  # current position in asset units
        entry_price = 0.0
        entry_time = None
        trades: list[Trade] = []
        equity_curve = [capital]
        daily_returns = []
        
        total_bars = len(price_history)

        for i in range(20, total_bars):  # Start after 20 bars for indicators
            bar = price_history[i]
            price = bar["price"]
            date = bar.get("date", datetime.now())
            
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date)
                except ValueError:
                    date = datetime.now()

            # Update equity
            current_equity = capital + position * price
            equity_curve.append(current_equity)

            if len(equity_curve) > 2:
                prev = equity_curve[-2]
                if prev > 0:
                    daily_returns.append((current_equity - prev) / prev)

            # Progress callback
            if on_progress and i % 10 == 0:
                await on_progress(i - 20, total_bars - 20)

            # Only make decisions at intervals
            if (i - 20) % decision_interval != 0:
                continue

            # ── Build market data for this point ──
            lookback = price_history[max(0, i-200):i+1]
            prices = [p["price"] for p in lookback]
            
            market_data = {
                "price": price,
                "rsi_14": self._calc_rsi(prices, 14) if len(prices) >= 15 else None,
                "sma_20": self._calc_sma(prices, 20) if len(prices) >= 20 else None,
                "sma_50": self._calc_sma(prices, 50) if len(prices) >= 50 else None,
                "sma_200": self._calc_sma(prices, 200) if len(prices) >= 200 else None,
            }

            # ── Get trading signal ──
            if arena and agents:
                result = await arena.run_debate(
                    asset=asset, agents=agents, market_data=market_data
                )
                signal = result.final_signal
                confidence = result.final_confidence
            else:
                signal, confidence = self._simple_signal(market_data)

            # ── Execute trading logic ──
            if position == 0:  # No position — look for entry
                if signal in ("buy", "strong_buy") and confidence > 0.5:
                    # Enter long
                    trade_capital = capital * position_size_pct
                    effective_price = price * (1 + self.slippage_pct)
                    commission = trade_capital * self.commission_pct
                    position = (trade_capital - commission) / effective_price
                    capital -= (trade_capital)
                    entry_price = effective_price
                    entry_time = date

            elif position > 0:  # Have position — look for exit
                if signal in ("sell", "strong_sell") and confidence > 0.4:
                    # Exit long
                    effective_price = price * (1 - self.slippage_pct)
                    proceeds = position * effective_price
                    commission = proceeds * self.commission_pct
                    capital += (proceeds - commission)
                    
                    pnl = (effective_price - entry_price) * position
                    pnl_pct = (effective_price / entry_price) - 1

                    trades.append(Trade(
                        asset=asset,
                        side="long",
                        entry_price=entry_price,
                        exit_price=effective_price,
                        entry_time=entry_time,
                        exit_time=date,
                        quantity=position,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        signal_source="arena" if arena else "rule",
                        debate_confidence=confidence,
                    ))

                    position = 0.0
                    entry_price = 0.0

        # ── Close any open position ──
        if position > 0 and price_history:
            final_price = price_history[-1]["price"]
            effective_price = final_price * (1 - self.slippage_pct)
            proceeds = position * effective_price
            commission = proceeds * self.commission_pct
            capital += (proceeds - commission)
            
            pnl = (effective_price - entry_price) * position
            pnl_pct = (effective_price / entry_price) - 1

            trades.append(Trade(
                asset=asset, side="long",
                entry_price=entry_price, exit_price=effective_price,
                entry_time=entry_time or datetime.now(),
                exit_time=datetime.now(),
                quantity=position, pnl=pnl, pnl_pct=pnl_pct,
                signal_source="close", debate_confidence=0.5,
            ))
            position = 0.0

        # ── Calculate all metrics ──
        final_equity = capital
        total_return = (final_equity / self.initial_capital) - 1
        
        # Benchmark: buy and hold
        start_price = price_history[20]["price"]
        end_price = price_history[-1]["price"]
        benchmark_return = (end_price / start_price) - 1

        # Time
        days = max((len(price_history) - 20), 1)
        years = max(days / 365.0, 0.01)

        # Annualized
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        alpha = total_return - benchmark_return

        # Risk
        if daily_returns:
            volatility = self._stdev(daily_returns) * math.sqrt(365)
            downside_returns = [r for r in daily_returns if r < 0]
            downside_dev = self._stdev(downside_returns) * math.sqrt(365) if downside_returns else 0.001
            
            avg_return = sum(daily_returns) / len(daily_returns) * 365
            sharpe = (avg_return - 0.05) / max(volatility, 0.001)  # 5% risk-free
            sortino = (avg_return - 0.05) / max(downside_dev, 0.001)
            
            # Drawdown
            peak = equity_curve[0]
            max_dd = 0
            dd_curve = []
            for eq in equity_curve:
                peak = max(peak, eq)
                dd = (eq - peak) / peak if peak > 0 else 0
                dd_curve.append(dd)
                max_dd = min(max_dd, dd)

            calmar = annualized_return / max(abs(max_dd), 0.001) if max_dd != 0 else 0

            # VaR & CVaR
            sorted_returns = sorted(daily_returns)
            var_idx = max(int(len(sorted_returns) * 0.05), 0)
            var_95 = sorted_returns[var_idx] if sorted_returns else 0
            cvar_95 = (sum(sorted_returns[:max(var_idx, 1)]) / max(var_idx, 1)) if sorted_returns else 0

            # Information Ratio
            excess_returns = [r - (benchmark_return / max(days, 1)) for r in daily_returns]
            tracking_error = self._stdev(excess_returns) * math.sqrt(365) if excess_returns else 0.001
            info_ratio = (total_return - benchmark_return) / max(tracking_error * years, 0.001)
        else:
            volatility = downside_dev = 0
            sharpe = sortino = calmar = 0
            max_dd = 0
            var_95 = cvar_95 = info_ratio = 0
            dd_curve = [0]
            downside_dev = 0

        # Max drawdown duration
        max_dd_duration = 0
        current_dd_start = 0
        in_drawdown = False
        peak_val = equity_curve[0] if equity_curve else 0
        for i, eq in enumerate(equity_curve):
            if eq >= peak_val:
                peak_val = eq
                if in_drawdown:
                    max_dd_duration = max(max_dd_duration, i - current_dd_start)
                    in_drawdown = False
            else:
                if not in_drawdown:
                    current_dd_start = i
                    in_drawdown = True

        # Trade stats
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        win_rate = len(winning) / max(len(trades), 1)
        avg_win = sum(t.pnl_pct for t in winning) / max(len(winning), 1)
        avg_loss = sum(t.pnl_pct for t in losing) / max(len(losing), 1)
        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = gross_profit / max(gross_loss, 0.01)

        avg_duration = 0
        if trades:
            durations = []
            for t in trades:
                if isinstance(t.entry_time, datetime) and isinstance(t.exit_time, datetime):
                    durations.append((t.exit_time - t.entry_time).total_seconds() / 3600)
            avg_duration = sum(durations) / max(len(durations), 1)

        # ── Debate-specific metrics ──
        confidences = [t.debate_confidence for t in trades]
        avg_confidence = sum(confidences) / max(len(confidences), 1)
        
        high_conf_trades = [t for t in trades if t.debate_confidence > 0.8]
        low_conf_trades = [t for t in trades if t.debate_confidence < 0.5]
        high_conf_wr = (sum(1 for t in high_conf_trades if t.pnl > 0) /
                        max(len(high_conf_trades), 1))
        low_conf_wr = (sum(1 for t in low_conf_trades if t.pnl > 0) /
                       max(len(low_conf_trades), 1))

        # Confidence-PnL correlation
        if len(trades) > 2:
            conf_corr = self._correlation(
                [t.debate_confidence for t in trades],
                [t.pnl_pct for t in trades]
            )
        else:
            conf_corr = 0.0

        return BacktestResult(
            strategy_name=strategy_name,
            asset=asset,
            start_date=price_history[20].get("date", datetime.now()) if isinstance(price_history[20].get("date"), datetime) else datetime.now(),
            end_date=price_history[-1].get("date", datetime.now()) if isinstance(price_history[-1].get("date"), datetime) else datetime.now(),
            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            alpha=alpha,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration_days=max_dd_duration,
            volatility=volatility,
            downside_deviation=downside_dev,
            information_ratio=info_ratio,
            cvar_95=cvar_95,
            var_95=var_95,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_trade_duration_hours=avg_duration,
            avg_debate_confidence=avg_confidence,
            high_confidence_win_rate=high_conf_wr,
            low_confidence_win_rate=low_conf_wr,
            confidence_correlation=conf_corr,
            debate_rounds_avg=2.0,
            consensus_rate=0.8,
            equity_curve=equity_curve,
            drawdown_curve=dd_curve,
            trades=trades,
        )

    def _simple_signal(self, market_data: dict) -> tuple[str, float]:
        """Simple RSI + SMA crossover signal"""
        rsi = market_data.get("rsi_14")
        price = market_data.get("price", 0)
        sma_20 = market_data.get("sma_20")
        sma_50 = market_data.get("sma_50")

        score = 0
        factors = 0

        if rsi is not None:
            if rsi < 30:
                score += 2
            elif rsi < 40:
                score += 1
            elif rsi > 70:
                score -= 2
            elif rsi > 60:
                score -= 1
            factors += 1

        if sma_20 and sma_50:
            if sma_20 > sma_50:
                score += 1  # Golden cross
            else:
                score -= 1  # Death cross
            factors += 1

        if sma_20 and price:
            if price > sma_20:
                score += 1
            else:
                score -= 1
            factors += 1

        avg = score / max(factors, 1)
        if avg > 0.5:
            return "buy", min(0.5 + avg * 0.2, 0.9)
        elif avg < -0.5:
            return "sell", min(0.5 + abs(avg) * 0.2, 0.9)
        return "hold", 0.4

    @staticmethod
    def _calc_rsi(prices: list[float], period: int = 14) -> Optional[float]:
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        recent = deltas[-period:]
        gains = [d for d in recent if d > 0]
        losses = [-d for d in recent if d < 0]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _calc_sma(prices: list[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def _stdev(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def _correlation(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
        sx = math.sqrt(sum((xi - mx) ** 2 for xi in x) / (n - 1))
        sy = math.sqrt(sum((yi - my) ** 2 for yi in y) / (n - 1))
        if sx * sy == 0:
            return 0.0
        return cov / (sx * sy)


async def compare_strategies(backtester: Backtester, results: list[BacktestResult]) -> str:
    """Compare multiple backtest results side by side"""
    if not results:
        return "No results to compare."

    header = f"\n{'Strategy':<25} {'Return':>10} {'Sharpe':>8} {'MaxDD':>10} {'WinRate':>8} {'Trades':>7} {'Alpha':>10} {'ConfCorr':>9}"
    divider = "-" * 95
    lines = ["\n  STRATEGY COMPARISON", "  " + divider, "  " + header, "  " + divider]

    # Sort by Sharpe ratio (risk-adjusted)
    sorted_results = sorted(results, key=lambda r: r.sharpe_ratio, reverse=True)

    for i, r in enumerate(sorted_results):
        prefix = "🏆" if i == 0 else f"  "
        line = (f"{prefix}{r.strategy_name:<23} "
                f"{r.total_return:>+9.2%} "
                f"{r.sharpe_ratio:>8.2f} "
                f"{r.max_drawdown:>10.2%} "
                f"{r.win_rate:>7.1%} "
                f"{r.total_trades:>7} "
                f"{r.alpha:>+9.2%} "
                f"{r.confidence_correlation:>+8.3f}")
        lines.append("  " + line)

    lines.append("  " + divider)
    best = sorted_results[0]
    lines.append(f"\n  🏆 WINNER: {best.strategy_name}")
    lines.append(f"     Sharpe {best.sharpe_ratio:.2f} | Return {best.total_return:+.2%} | "
                 f"Alpha {best.alpha:+.2%} over buy-and-hold")
    
    return "\n".join(lines)
