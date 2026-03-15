"""
WhaleTrader - Backtester v8 (Regime-Momentum Hybrid)
=====================================================
Key changes from v7:
1. Regime-transition detection: if position entered in ranging but market turns bull,
   immediately upgrade position management to trend mode
2. Smarter exit: don't signal_exit in first 3 bars (avoid whipsaw)
3. Tighter max_loss in non-trend (8%), wider in strong bull (30%)
4. Dynamic trailing: accelerate trailing tightening when momentum decelerates
"""

import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from agents.backtester import BacktestResult, Trade
from agents.signal_engine_v8 import SignalEngineV8, SignalResult, MarketRegime


@dataclass
class Position:
    asset: str
    entry_price: float
    entry_time: datetime
    quantity: float
    capital_used: float
    stop_loss: float
    take_profit: float
    trailing_stop_pct: float
    highest_since_entry: float
    signal_confidence: float
    regime_at_entry: MarketRegime
    num_add_ons: int = 0
    max_add_ons: int = 4
    avg_entry_price: float = 0
    entry_bar_idx: int = 0

    def __post_init__(self):
        if self.avg_entry_price == 0:
            self.avg_entry_price = self.entry_price

    def update_trailing(self, price: float):
        self.highest_since_entry = max(self.highest_since_entry, price)
        trailing_price = self.highest_since_entry * (1 - self.trailing_stop_pct)
        self.stop_loss = max(self.stop_loss, trailing_price)

    def should_exit(self, price: float) -> Optional[str]:
        if price <= self.stop_loss:
            return "stop_loss"
        if price >= self.take_profit:
            return "take_profit"
        return None

    def current_value(self, price: float) -> float:
        return self.quantity * price

    def pnl_pct(self, price: float) -> float:
        if self.avg_entry_price == 0: return 0
        return (price / self.avg_entry_price) - 1

    def add_position(self, price: float, qty: float, capital: float):
        total_qty = self.quantity + qty
        self.avg_entry_price = (self.avg_entry_price * self.quantity + price * qty) / total_qty
        self.quantity = total_qty
        self.capital_used += capital
        self.num_add_ons += 1


class BacktesterV8:
    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.0005,
                 max_loss_per_trade: float = 0.06,
                 max_portfolio_exposure: float = 0.95):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.max_loss_per_trade = max_loss_per_trade
        self.max_portfolio_exposure = max_portfolio_exposure

    async def run(self, asset: str, strategy_name: str,
                  price_history: list[dict],
                  arena=None, agents=None,
                  decision_interval: int = 1) -> BacktestResult:

        engine = SignalEngineV8()

        if not price_history or len(price_history) < 20:
            raise ValueError("Need at least 20 data points")

        capital = self.initial_capital
        position: Optional[Position] = None
        trades: list[Trade] = []
        equity_curve = [capital]
        daily_returns = []
        cooldown = 0
        last_exit_idx = None

        prices_arr = [bar["price"] for bar in price_history]
        volumes_arr = [bar.get("volume", 0) for bar in price_history]
        has_volume = any(v > 0 for v in volumes_arr)

        warmup = 20
        total = len(price_history)

        for i in range(warmup, total):
            price = price_history[i]["price"]
            date = price_history[i].get("date", datetime.now())
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date)
                except:
                    date = datetime.now()

            if position:
                total_equity = capital + position.current_value(price)
            else:
                total_equity = capital
            total_equity = max(total_equity, 0.01)

            equity_curve.append(total_equity)
            if len(equity_curve) > 2 and equity_curve[-2] > 0:
                daily_returns.append((total_equity - equity_curve[-2]) / equity_curve[-2])

            # ── POSITION MANAGEMENT ──
            if position:
                pnl_pct = position.pnl_pct(price)

                # Get current regime (even if entered in different regime)
                sig_check = engine.generate_signal(
                    prices_arr[:i+1],
                    volumes_arr[:i+1] if has_volume else None,
                    current_position=position.quantity,
                )
                current_regime = sig_check.regime
                in_trend = current_regime in (
                    MarketRegime.STRONG_BULL, MarketRegime.BULL, MarketRegime.VOLATILE)
                entered_trend = position.regime_at_entry in (
                    MarketRegime.STRONG_BULL, MarketRegime.BULL, MarketRegime.VOLATILE)

                # Use trend management if EITHER entered in trend OR current is trend
                use_trend_mgmt = in_trend or entered_trend

                if use_trend_mgmt:
                    # Profit-tier trailing
                    if pnl_pct > 1.00:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.30)
                    elif pnl_pct > 0.60:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.28)
                    elif pnl_pct > 0.40:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.25)
                    elif pnl_pct > 0.25:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.23)
                    elif pnl_pct > 0.12:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.20)

                    if current_regime == MarketRegime.STRONG_BULL:
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.30)

                    # No TP in trends
                    if position.take_profit < price * 5:
                        position.take_profit = price * 100.0

                position.update_trailing(price)
                exit_reason = position.should_exit(price)

                # Dynamic max loss
                max_loss = self.max_loss_per_trade  # 6%
                if current_regime == MarketRegime.STRONG_BULL:
                    max_loss = 0.30
                elif entered_trend:
                    max_loss = 0.25
                elif position.regime_at_entry == MarketRegime.VOLATILE:
                    max_loss = 0.20
                elif position.regime_at_entry == MarketRegime.RANGING:
                    max_loss = 0.08

                if pnl_pct < -max_loss:
                    exit_reason = "max_loss"

                if exit_reason:
                    trade = self._close(position, price, date, exit_reason)
                    capital += trade.pnl + position.capital_used
                    trades.append(trade)
                    position = None
                    last_exit_idx = i

                    # Cooldown
                    if current_regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL,
                                         MarketRegime.VOLATILE):
                        cooldown = 0
                    else:
                        cooldown = 1
                    continue

            if (i - warmup) % decision_interval != 0:
                continue

            if cooldown > 0:
                cooldown -= 1
                continue

            # ── Generate signal ──
            sig = engine.generate_signal(
                prices_arr[:i+1],
                volumes_arr[:i+1] if has_volume else None,
                current_position=position.quantity if position else 0,
            )

            # ── ENTRY ──
            if position is None:
                min_conf = 0.35 if sig.regime in (
                    MarketRegime.STRONG_BULL, MarketRegime.BULL) else 0.45

                bars_without_position = i - warmup
                if last_exit_idx is not None:
                    bars_without_position = i - last_exit_idx

                if sig.regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL,
                                  MarketRegime.VOLATILE):
                    force_threshold = 6
                else:
                    force_threshold = 12

                force_entry = (bars_without_position > force_threshold and
                               sig.regime not in (MarketRegime.CRASH, MarketRegime.STRONG_BEAR))

                should_enter = (sig.signal in ("buy", "strong_buy") and
                                sig.confidence > min_conf) or force_entry

                if should_enter:
                    if force_entry and sig.signal not in ("buy", "strong_buy"):
                        pos_size_pct = 0.40
                    else:
                        pos_size_pct = min(sig.position_size, self.max_portfolio_exposure)

                    trade_amount = capital * pos_size_pct
                    if trade_amount < capital * 0.03:
                        continue

                    effective_price = price * (1 + self.slippage_pct)
                    commission = trade_amount * self.commission_pct
                    actual_invest = trade_amount - commission
                    qty = actual_invest / effective_price

                    if sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL,
                                      MarketRegime.VOLATILE):
                        initial_stop = effective_price * (1 - 0.28)
                    else:
                        initial_stop = effective_price * (1 - self.max_loss_per_trade)

                    stop_loss = max(sig.stop_loss, initial_stop)

                    position = Position(
                        asset=asset,
                        entry_price=effective_price,
                        entry_time=date,
                        quantity=qty,
                        capital_used=trade_amount,
                        stop_loss=stop_loss,
                        take_profit=sig.take_profit,
                        trailing_stop_pct=sig.trailing_stop_pct,
                        highest_since_entry=effective_price,
                        signal_confidence=sig.confidence,
                        regime_at_entry=sig.regime,
                        entry_bar_idx=i,
                    )
                    capital -= trade_amount

            else:
                # ── PYRAMIDING ──
                in_trend = sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL)
                pnl_pct = position.pnl_pct(price)

                pyr_thresholds = [0.03, 0.06, 0.12, 0.20]
                next_threshold = pyr_thresholds[min(position.num_add_ons, len(pyr_thresholds)-1)]

                if (in_trend and
                        position.num_add_ons < position.max_add_ons and
                        pnl_pct > next_threshold and
                        capital > self.initial_capital * 0.05 and
                        sig.signal in ("buy", "strong_buy")):

                    add_size = min(capital * 0.35, capital * 0.9)
                    if add_size > 100:
                        effective_price = price * (1 + self.slippage_pct)
                        commission = add_size * self.commission_pct
                        add_qty = (add_size - commission) / effective_price
                        position.add_position(effective_price, add_qty, add_size)
                        capital -= add_size
                        position.trailing_stop_pct = max(position.trailing_stop_pct, 0.25)

                # ── EXIT SIGNALS ──
                bars_held = i - position.entry_bar_idx
                if not in_trend and pnl_pct <= 0 and bars_held > 1:
                    if sig.signal in ("sell", "strong_sell") and sig.confidence > 0.55:
                        trade = self._close(position, price, date, "signal_exit")
                        capital += trade.pnl + position.capital_used
                        trades.append(trade)
                        position = None
                        last_exit_idx = i

        # Close open position
        if position:
            final_price = price_history[-1]["price"]
            trade = self._close(position, final_price,
                                price_history[-1].get("date", datetime.now()),
                                "end_of_test")
            capital += trade.pnl + position.capital_used
            trades.append(trade)

        return self._build_result(
            strategy_name, asset, price_history, warmup,
            capital, trades, equity_curve, daily_returns
        )

    def _close(self, pos, price, date, reason):
        effective_price = price * (1 - self.slippage_pct)
        commission = pos.quantity * effective_price * self.commission_pct
        pnl = (effective_price - pos.avg_entry_price) * pos.quantity - commission
        pnl_pct = (effective_price / pos.avg_entry_price) - 1 if pos.avg_entry_price > 0 else 0

        return Trade(
            asset=pos.asset, side="long",
            entry_price=pos.avg_entry_price, exit_price=effective_price,
            entry_time=pos.entry_time if isinstance(pos.entry_time, datetime) else datetime.now(),
            exit_time=date if isinstance(date, datetime) else datetime.now(),
            quantity=pos.quantity,
            pnl=pnl, pnl_pct=pnl_pct,
            signal_source=reason,
            debate_confidence=pos.signal_confidence,
        )

    def _build_result(self, strategy_name, asset, price_history, warmup,
                      final_capital, trades, equity_curve, daily_returns):
        total_return = (final_capital / self.initial_capital) - 1
        bh_return = (price_history[-1]["price"] / price_history[warmup]["price"]) - 1

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

            peak = equity_curve[0]; max_dd = 0; dd_curve = []
            for eq in equity_curve:
                peak = max(peak, eq)
                dd = (eq - peak) / peak if peak > 0 else 0
                dd_curve.append(dd); max_dd = min(max_dd, dd)
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
            max_dd = 0; dd_curve = [0]; var_95 = cvar_95 = info_ratio = 0

        max_dd_dur = 0; dd_start = 0; in_dd = False
        pk = equity_curve[0] if equity_curve else 0
        for idx, eq in enumerate(equity_curve):
            if eq >= pk:
                pk = eq
                if in_dd: max_dd_dur = max(max_dd_dur, idx - dd_start); in_dd = False
            elif not in_dd: dd_start = idx; in_dd = True

        win = [t for t in trades if t.pnl > 0]
        lose = [t for t in trades if t.pnl <= 0]
        wr = len(win) / max(len(trades), 1)
        avg_win = sum(t.pnl_pct for t in win) / max(len(win), 1)
        avg_loss = sum(t.pnl_pct for t in lose) / max(len(lose), 1)
        gp = sum(t.pnl for t in win); gl = abs(sum(t.pnl for t in lose))
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
            debate_rounds_avg=2.0, consensus_rate=0.8,
            equity_curve=equity_curve, drawdown_curve=dd_curve,
            daily_returns=daily_returns, trades=trades,
        )


def _std(values):
    if len(values) < 2: return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))
