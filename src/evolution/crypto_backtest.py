"""
Crypto Backtest Engine
======================
A separate backtest engine for cryptocurrency markets.
Designed to be used by AutoEvolver when market="crypto".

Key differences from A-share backtest:
1. No T+1 restriction — can buy and sell in same period
2. No limit-up/down — crypto has no daily price limits
3. 24/7 trading — no market hours restriction
4. Short selling support — crypto perpetuals allow shorting
5. Leverage support — 1x-10x configurable leverage
6. Maker/taker fees — default 0.02% maker, 0.04% taker (Binance rate)
7. Funding rate — for perpetuals, charge every 8 hours
8. Liquidation check — if using leverage, check if position would be liquidated
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


class CryptoBacktestEngine:
    """Backtest engine for crypto perpetual futures / spot markets.

    Args:
        leverage: Position leverage (1-10). 1 = spot, >1 = perpetual futures.
        fee_maker: Maker fee rate (default 0.02% = 0.0002).
        fee_taker: Taker fee rate (default 0.04% = 0.0004).
        funding_rate: Funding rate per interval (default 0.01% = 0.0001).
        funding_interval: Hours between funding charges (default 8).
        periods_per_day: Number of data periods per day (24 for hourly, 1 for daily).
    """

    def __init__(
        self,
        leverage: int = 1,
        fee_maker: float = 0.0002,
        fee_taker: float = 0.0004,
        funding_rate: float = 0.0001,
        funding_interval: int = 8,
        periods_per_day: int = 24,
    ):
        if leverage < 1 or leverage > 10:
            raise ValueError(f"Leverage must be 1-10, got {leverage}")
        self.leverage = leverage
        self.fee_maker = fee_maker
        self.fee_taker = fee_taker
        self.funding_rate = funding_rate
        self.funding_interval = funding_interval
        self.periods_per_day = periods_per_day

    def _compute_funding_charges(
        self,
        entry_period: int,
        exit_period: int,
        position_value: float,
        is_short: bool,
    ) -> float:
        """Compute total funding charges for a position held between two periods.

        For longs: funding is a cost (deducted).
        For shorts: funding is received (added) — but we simplify and charge
        the same rate in opposite direction.

        Args:
            entry_period: Period index when position was opened.
            exit_period: Period index when position was closed.
            position_value: Notional position value (entry_price * shares * leverage).
            is_short: Whether this is a short position.

        Returns:
            Total funding cost (positive = cost, negative = income).
        """
        if self.leverage <= 1:
            # Spot trading — no funding
            return 0.0

        # How many hours does the position span?
        periods_held = exit_period - entry_period
        hours_held = periods_held * (24.0 / self.periods_per_day)

        # Number of funding intervals
        num_fundings = int(hours_held / self.funding_interval)

        if num_fundings <= 0:
            return 0.0

        # Longs pay funding, shorts receive (simplified: opposite sign)
        direction = 1.0 if not is_short else -1.0
        total_funding = position_value * self.funding_rate * num_fundings * direction

        return total_funding

    def _check_liquidation(
        self,
        entry_price: float,
        current_price: float,
        is_short: bool,
    ) -> bool:
        """Check if a leveraged position would be liquidated.

        Liquidation occurs when the loss exceeds the margin (initial investment).
        With N× leverage, a 1/N adverse move wipes out the margin.

        For longs: liquidated if price drops by >= 1/leverage from entry.
        For shorts: liquidated if price rises by >= 1/leverage from entry.

        Args:
            entry_price: Entry price of the position.
            current_price: Current market price.
            is_short: Whether this is a short position.

        Returns:
            True if position would be liquidated.
        """
        if self.leverage <= 1:
            return False

        if entry_price <= 0:
            return False

        liquidation_threshold = 1.0 / self.leverage

        if is_short:
            # Short: liquidated if price rises too much
            price_change = (current_price - entry_price) / entry_price
            return price_change >= liquidation_threshold
        else:
            # Long: liquidated if price drops too much
            price_change = (entry_price - current_price) / entry_price
            return price_change >= liquidation_threshold

    def _compute_pnl(
        self,
        entry_price: float,
        exit_price: float,
        shares: float,
        is_short: bool,
        entry_period: int,
        exit_period: int,
        was_liquidated: bool = False,
    ) -> Tuple[float, float]:
        """Compute PnL for a single trade including fees and funding.

        Args:
            entry_price: Entry price.
            exit_price: Exit price.
            shares: Number of units (base quantity).
            is_short: Whether this is a short position.
            entry_period: Period index of entry.
            exit_period: Period index of exit.
            was_liquidated: Whether the position was liquidated.

        Returns:
            (trade_return_pct, pnl_absolute) tuple.
        """
        # Notional value at entry
        notional = entry_price * shares * self.leverage

        # Fees: entry uses taker (market order), exit uses taker
        entry_fee = entry_price * shares * self.fee_taker
        exit_fee = exit_price * shares * self.fee_taker

        if was_liquidated:
            # Liquidation: lose entire margin (100% of invested capital)
            margin = entry_price * shares  # capital put up
            pnl = -margin
            trade_return = -100.0
        else:
            # Price PnL
            if is_short:
                price_pnl = (entry_price - exit_price) * shares * self.leverage
            else:
                price_pnl = (exit_price - entry_price) * shares * self.leverage

            # Funding charges
            funding = self._compute_funding_charges(
                entry_period, exit_period, notional, is_short
            )

            # Total PnL
            pnl = price_pnl - entry_fee - exit_fee - funding

            # Return as % of margin (invested capital)
            margin = entry_price * shares
            trade_return = (pnl / margin * 100) if margin > 0 else 0.0

        return trade_return, pnl

    def run_backtest(
        self,
        dna,  # StrategyDNA
        data: Dict[str, Dict[str, list]],
        indicators: Dict[str, Dict[str, Any]],
        codes: List[str],
        day_start: int,
        day_end: int,
    ) -> Tuple[
        float, float, float, float, float, int, float, float, int,
        List[float], int, float
    ]:
        """Run crypto backtest on a date range.

        Returns same tuple format as A-share _run_backtest:
        (annual_return, max_drawdown, win_rate, sharpe, calmar, total_trades,
         profit_factor, sortino, max_consec_losses, monthly_returns,
         max_concurrent_positions, avg_turnover)
        """
        # Import score_stock from auto_evolve (lazy to avoid circular imports)
        from src.evolution.auto_evolve import score_stock

        initial_capital = 1_000_000.0
        capital = initial_capital
        portfolio_values = [capital]

        trades: List[float] = []
        gross_profit = 0.0
        gross_loss = 0.0

        # Monthly return tracking
        monthly_returns: List[float] = []
        month_start_capital = capital
        last_month_period = day_start
        # For crypto: ~30 days worth of periods
        approx_month_periods = 30 * self.periods_per_day

        # Track max concurrent positions
        max_concurrent = 0

        # Track turnover
        turnover_ratios: List[float] = []
        prev_picks: set = set()

        hold_periods = max(1, dna.hold_days)  # Crypto: min 1 period (no T+1)

        period = day_start

        while period < day_end - hold_periods:
            # Monthly return tracking
            if period - last_month_period >= approx_month_periods:
                if month_start_capital > 0:
                    mr = (capital - month_start_capital) / month_start_capital * 100
                    monthly_returns.append(mr)
                month_start_capital = capital
                last_month_period = period

            # Score all assets at this period
            scored: List[Tuple[str, float, bool]] = []
            for code in codes:
                sd = data[code]
                if period >= len(sd["close"]):
                    continue
                ind = indicators[code]
                s = score_stock(period, ind, dna)

                # Determine direction: high score = long, low score = short
                if s >= dna.min_score:
                    scored.append((code, s, False))  # Long
                elif self.leverage > 1 and s <= (10 - dna.min_score):
                    # Low score = short signal (only with leverage/perpetuals)
                    scored.append((code, 10 - s, True))  # Short

            # Pick top max_positions
            scored.sort(key=lambda x: x[1], reverse=True)
            picks = scored[: dna.max_positions]

            # Track turnover
            current_pick_codes = {code for code, _, _ in picks}
            if prev_picks:
                changes = len(prev_picks.symmetric_difference(current_pick_codes))
                max_pos = max(dna.max_positions, 1)
                period_turnover = changes / max_pos
                turnover_ratios.append(period_turnover)
            prev_picks = current_pick_codes

            if picks:
                per_pos = capital / len(picks)
                positions_this_period = 0

                for code, _score, is_short in picks:
                    sd = data[code]

                    # Crypto: can enter in same period (no T+1)
                    entry_period = period
                    if entry_period >= len(sd["close"]):
                        continue

                    entry_price = sd["open"][entry_period]
                    if entry_price <= 0:
                        continue

                    # No limit-up/down check for crypto

                    shares = per_pos / entry_price  # base quantity
                    exit_price = entry_price
                    was_liquidated = False
                    actual_exit_period = entry_period

                    for d in range(entry_period, min(entry_period + hold_periods, len(sd["close"]))):
                        low = sd["low"][d]
                        high = sd["high"][d]
                        close = sd["close"][d]

                        # No limit-down check for crypto

                        # Liquidation check (leveraged positions)
                        if self.leverage > 1:
                            worst_price = low if not is_short else high
                            if self._check_liquidation(entry_price, worst_price, is_short):
                                was_liquidated = True
                                actual_exit_period = d
                                break

                        # Stop loss
                        if is_short:
                            sl_price = entry_price * (1 + dna.stop_loss_pct / 100)
                            if high >= sl_price:
                                exit_price = sl_price
                                actual_exit_period = d
                                break
                            tp_price = entry_price * (1 - dna.take_profit_pct / 100)
                            if low <= tp_price:
                                exit_price = tp_price
                                actual_exit_period = d
                                break
                        else:
                            sl_price = entry_price * (1 - dna.stop_loss_pct / 100)
                            if low <= sl_price:
                                exit_price = sl_price
                                actual_exit_period = d
                                break
                            tp_price = entry_price * (1 + dna.take_profit_pct / 100)
                            if high >= tp_price:
                                exit_price = tp_price
                                actual_exit_period = d
                                break

                        exit_price = close
                        actual_exit_period = d

                    # Compute PnL
                    trade_return, pnl = self._compute_pnl(
                        entry_price, exit_price, shares, is_short,
                        entry_period, actual_exit_period, was_liquidated,
                    )

                    trades.append(trade_return)
                    if pnl > 0:
                        gross_profit += pnl
                    else:
                        gross_loss += abs(pnl)

                    capital += pnl
                    positions_this_period += 1

                if positions_this_period > max_concurrent:
                    max_concurrent = positions_this_period

            portfolio_values.append(max(capital, 0.01))
            period += hold_periods

        # Final partial month
        if month_start_capital > 0 and capital != month_start_capital:
            mr = (capital - month_start_capital) / month_start_capital * 100
            monthly_returns.append(mr)

        # ── Compute metrics ──
        total_trades = len(trades)
        win_rate = 0.0
        if total_trades > 0:
            wins = sum(1 for t in trades if t > 0)
            win_rate = wins / total_trades * 100

        # Max consecutive losses
        max_consec_losses = 0
        current_streak = 0
        for t in trades:
            if t <= 0:
                current_streak += 1
                max_consec_losses = max(max_consec_losses, current_streak)
            else:
                current_streak = 0

        # Annual return — crypto uses 365 days (24/7 market)
        annual_return = 0.0
        if len(portfolio_values) > 1 and portfolio_values[0] > 0:
            total_return = portfolio_values[-1] / portfolio_values[0] - 1
            periods_used = day_end - day_start
            # Convert periods to years: periods / periods_per_year
            periods_per_year = 365 * self.periods_per_day
            years = periods_used / periods_per_year if periods_used > 0 else 1
            if total_return > -1:
                annual_return = ((1 + total_return) ** (1 / max(years, 0.01)) - 1) * 100
            else:
                annual_return = -100.0

        # Max drawdown
        max_drawdown = 0.0
        peak = portfolio_values[0]
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, dd)

        # Sharpe ratio — use periods_per_year for annualization
        sharpe = 0.0
        sortino = 0.0
        if len(portfolio_values) > 2:
            period_returns = [
                (portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1]
                for i in range(1, len(portfolio_values))
                if portfolio_values[i - 1] > 0
            ]
            if period_returns:
                mean_r = sum(period_returns) / len(period_returns)
                var_r = sum((r - mean_r) ** 2 for r in period_returns) / len(period_returns)
                std_r = math.sqrt(var_r) if var_r > 0 else 0.001

                # Periods per year: for crypto with hourly data = 365*24 = 8760
                periods_per_year = 365 * self.periods_per_day / max(hold_periods, 1)
                sharpe = (mean_r / std_r) * math.sqrt(periods_per_year)

                # Sortino
                downside_returns = [r for r in period_returns if r < 0]
                if downside_returns:
                    downside_var = sum(r ** 2 for r in downside_returns) / len(period_returns)
                    downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.001
                    sortino = (mean_r / downside_std) * math.sqrt(periods_per_year)
                else:
                    sortino = sharpe * 1.5

        calmar = annual_return / max(max_drawdown, 1.0)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
            10.0 if gross_profit > 0 else 0.0
        )

        # Average turnover
        avg_turnover = 0.0
        if turnover_ratios:
            avg_turnover = sum(turnover_ratios) / len(turnover_ratios)

        return (
            annual_return, max_drawdown, win_rate, sharpe, calmar,
            total_trades, profit_factor, sortino, max_consec_losses,
            monthly_returns, max_concurrent, avg_turnover,
        )
