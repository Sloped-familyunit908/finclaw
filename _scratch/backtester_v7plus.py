"""
WhaleTrader v7+ — Long/Short Engine
=====================================
Extends v7: adds short selling in bear/strong_bear/crash regimes.
"""
import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from agents.backtester_v7 import BacktesterV7, Position
from agents.backtester import BacktestResult, Trade
from agents.signal_engine_v7 import SignalEngineV7, SignalResult, MarketRegime


@dataclass
class ShortPosition:
    """Short position: profits when price goes down."""
    asset: str
    entry_price: float
    entry_time: datetime
    quantity: float
    capital_used: float  # collateral
    stop_loss: float     # above entry (buy back if price rises)
    take_profit: float   # below entry (buy back if price drops)
    trailing_stop_pct: float
    lowest_since_entry: float
    signal_confidence: float
    regime_at_entry: MarketRegime
    entry_bar_idx: int = 0
    avg_entry_price: float = 0

    def __post_init__(self):
        if self.avg_entry_price == 0:
            self.avg_entry_price = self.entry_price

    def update_trailing(self, price: float):
        self.lowest_since_entry = min(self.lowest_since_entry, price)
        trailing_price = self.lowest_since_entry * (1 + self.trailing_stop_pct)
        self.stop_loss = min(self.stop_loss, trailing_price)

    def should_exit(self, price: float) -> Optional[str]:
        if price >= self.stop_loss:
            return "stop_loss"
        if price <= self.take_profit:
            return "take_profit"
        return None

    def pnl(self, price: float) -> float:
        return (self.avg_entry_price - price) * self.quantity

    def pnl_pct(self, price: float) -> float:
        if self.avg_entry_price == 0: return 0
        return (self.avg_entry_price - price) / self.avg_entry_price

    def current_value(self, price: float) -> float:
        return self.capital_used + self.pnl(price)


class BacktesterV7Plus(BacktesterV7):
    """Long/Short backtester. Inherits all long-side logic from v7,
    adds short selling capability in bear regimes."""

    def __init__(self, enable_short=True, short_borrow_rate=0.0002, **kwargs):
        super().__init__(**kwargs)
        self.enable_short = enable_short
        self.short_borrow_rate = short_borrow_rate

    async def run(self, asset, strategy_name, price_history,
                  arena=None, agents=None, decision_interval=1):

        engine = SignalEngineV7()
        if not price_history or len(price_history) < 20:
            raise ValueError("Need at least 20 data points")

        capital = self.initial_capital
        long_pos: Optional[Position] = None
        short_pos: Optional[ShortPosition] = None
        trades = []
        equity_curve = [capital]
        daily_returns = []
        cooldown = 0
        consecutive_losses = 0

        prices_arr = [bar["price"] for bar in price_history]
        volumes_arr = [bar.get("volume", 0) for bar in price_history]
        has_volume = any(v > 0 for v in volumes_arr)
        warmup = 20

        for i in range(warmup, len(price_history)):
            price = prices_arr[i]
            date = price_history[i].get("date", datetime.now())

            # Generate signal once per bar (engine is stateful!)
            sig = engine.generate_signal(
                prices_arr[:i+1],
                volumes_arr[:i+1] if has_volume else None,
                current_position=(long_pos.quantity if long_pos else 
                                  (-short_pos.quantity if short_pos else 0)),
            )

            # Equity tracking
            eq = capital
            if long_pos:
                eq += long_pos.quantity * price
            if short_pos:
                eq += short_pos.current_value(price)
            equity_curve.append(eq)
            if len(equity_curve) > 1:
                daily_returns.append(equity_curve[-1] / equity_curve[-2] - 1)

            # ── MANAGE LONG POSITION (same as v7) ──
            if long_pos:
                long_pos.update_trailing(price)
                exit_reason = long_pos.should_exit(price)
                pnl_pct = long_pos.pnl_pct(price)

                if not long_pos.breakeven_triggered and pnl_pct > 0.08:
                    long_pos.stop_loss = max(long_pos.stop_loss, long_pos.avg_entry_price * 1.005)
                    long_pos.breakeven_triggered = True

                if pnl_pct > 0.30:
                    long_pos.trailing_stop_pct = min(long_pos.trailing_stop_pct, 0.30)
                elif pnl_pct > 0.20:
                    long_pos.trailing_stop_pct = min(long_pos.trailing_stop_pct, 0.35)
                elif pnl_pct > 0.10:
                    long_pos.trailing_stop_pct = min(long_pos.trailing_stop_pct, 0.40)

                max_loss = self.max_loss_per_trade
                if long_pos.regime_at_entry in (MarketRegime.STRONG_BULL,):
                    max_loss = 0.30
                elif long_pos.regime_at_entry in (MarketRegime.BULL,):
                    max_loss = 0.25
                elif long_pos.regime_at_entry == MarketRegime.VOLATILE:
                    max_loss = 0.20
                elif long_pos.regime_at_entry == MarketRegime.RANGING:
                    max_loss = 0.08

                if pnl_pct < -max_loss:
                    exit_reason = "max_loss"

                if exit_reason:
                    trade = self._close(long_pos, price, date, exit_reason)
                    capital += trade.pnl + long_pos.capital_used
                    trades.append(trade)
                    if trade.pnl < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0
                    long_pos = None
                    cooldown_sig = sig  # use same bar's signal for cooldown
                    if cooldown_sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL,
                                           MarketRegime.VOLATILE):
                        cooldown = 0
                    else:
                        cooldown = min(1 + consecutive_losses, 4)
                    continue

                # Pyramiding
                in_trend = sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL)
                pyr_thresholds = [0.03, 0.06, 0.12, 0.20]
                next_thr = pyr_thresholds[min(long_pos.num_add_ons, len(pyr_thresholds)-1)]
                if (in_trend and long_pos.num_add_ons < long_pos.max_add_ons
                    and pnl_pct > next_thr and capital > self.initial_capital * 0.05
                    and sig.signal in ("buy", "strong_buy")):
                    add_size = min(capital * 0.35, capital * 0.9)
                    if add_size > 100:
                        ep = price * (1 + self.slippage_pct)
                        comm = add_size * self.commission_pct
                        add_qty = (add_size - comm) / ep
                        long_pos.add_position(ep, add_qty, add_size)
                        capital -= add_size
                        long_pos.trailing_stop_pct = max(long_pos.trailing_stop_pct, 0.25)

                # Signal exit
                bars_held = i - long_pos.entry_bar_idx
                if not in_trend and pnl_pct <= 0 and bars_held > 1:
                    if sig.signal in ("sell", "strong_sell") and sig.confidence > 0.55:
                        trade = self._close(long_pos, price, date, "signal_exit")
                        capital += trade.pnl + long_pos.capital_used
                        trades.append(trade)
                        long_pos = None
                continue

            # ── MANAGE SHORT POSITION ──
            if short_pos:
                short_pos.update_trailing(price)

                # Daily borrow cost
                capital -= short_pos.capital_used * self.short_borrow_rate

                exit_reason = short_pos.should_exit(price)
                pnl_pct = short_pos.pnl_pct(price)

                # Max loss for shorts: 10%
                if pnl_pct < -0.10:
                    exit_reason = "max_loss"

                # Regime shift: close short if market turns bull
                if (sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL)
                    and pnl_pct < 0.03):
                    exit_reason = "regime_shift"

                # Profit-tier trailing for shorts
                if pnl_pct > 0.12:
                    short_pos.trailing_stop_pct = min(short_pos.trailing_stop_pct, 0.04)
                elif pnl_pct > 0.06:
                    short_pos.trailing_stop_pct = min(short_pos.trailing_stop_pct, 0.06)

                if exit_reason:
                    # Close short
                    ep = price * (1 + self.slippage_pct)
                    pnl_val = short_pos.pnl(ep)
                    comm = abs(pnl_val) * self.commission_pct if pnl_val > 0 else 0
                    pnl_val -= comm
                    trade = Trade(
                        asset=short_pos.asset, side="short",
                        entry_price=short_pos.avg_entry_price, exit_price=ep,
                        entry_time=short_pos.entry_time, exit_time=date,
                        quantity=short_pos.quantity,
                        pnl=pnl_val, pnl_pct=short_pos.pnl_pct(ep),
                        signal_source=exit_reason,
                        debate_confidence=short_pos.signal_confidence,
                    )
                    capital += short_pos.capital_used + pnl_val
                    trades.append(trade)
                    if pnl_val < 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0
                    short_pos = None
                    cooldown = 2
                continue

            # ── ENTRY LOGIC (no position) ──
            if (i - warmup) % decision_interval != 0:
                continue
            if cooldown > 0:
                cooldown -= 1
                continue

            if capital < self.initial_capital * 0.03:
                continue

            in_trend = sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL)

            # LONG ENTRY (same as v7)
            if sig.signal in ("buy", "strong_buy"):
                if in_trend:
                    pos_size = sig.position_size
                else:
                    pos_size = sig.position_size

                size = capital * pos_size * self.max_portfolio_exposure
                if size >= 100:
                    ep = price * (1 + self.slippage_pct)
                    comm = size * self.commission_pct
                    qty = (size - comm) / ep
                    long_pos = Position(
                        asset=asset, entry_price=ep, entry_time=date,
                        quantity=qty, capital_used=size,
                        stop_loss=sig.stop_loss, take_profit=sig.take_profit,
                        trailing_stop_pct=sig.trailing_stop_pct,
                        highest_since_entry=ep,
                        signal_confidence=sig.confidence,
                        regime_at_entry=sig.regime,
                        entry_bar_idx=i,
                    )
                    capital -= size

            # SHORT ENTRY (new in v7+)
            elif (self.enable_short
                  and sig.regime in (MarketRegime.STRONG_BEAR, MarketRegime.CRASH)
                  and sig.signal == "hold"
                  and sig.confidence > 0.55):

                # Strict momentum check: confirmed strong downtrend
                n = min(i+1, len(prices_arr))
                ret_10 = prices_arr[i] / prices_arr[max(0, i-10)] - 1 if i > 10 else 0
                ret_5 = prices_arr[i] / prices_arr[max(0, i-5)] - 1 if i > 5 else 0
                ret_20 = prices_arr[i] / prices_arr[max(0, i-20)] - 1 if i > 20 else 0

                if ret_20 < -0.08 and ret_10 < -0.04 and ret_5 < -0.01:
                    short_pct = 0.20 if sig.regime == MarketRegime.STRONG_BEAR else 0.12
                    if sig.regime == MarketRegime.CRASH:
                        short_pct = 0.25

                    size = capital * short_pct
                    if size >= 100:
                        ep = price * (1 - self.slippage_pct)
                        comm = size * self.commission_pct
                        qty = (size - comm) / ep

                        atr = self._quick_atr(prices_arr[:i+1])
                        short_pos = ShortPosition(
                            asset=asset, entry_price=ep, entry_time=date,
                            quantity=qty, capital_used=size,
                            stop_loss=ep * 1.08,
                            take_profit=ep - atr * 3.0,
                            trailing_stop_pct=0.08,
                            lowest_since_entry=ep,
                            signal_confidence=sig.confidence,
                            regime_at_entry=sig.regime,
                            entry_bar_idx=i,
                        )
                        capital -= size

        # Close open positions
        if long_pos:
            trade = self._close(long_pos, prices_arr[-1],
                               price_history[-1].get("date", datetime.now()), "end_of_test")
            capital += trade.pnl + long_pos.capital_used
            trades.append(trade)
        if short_pos:
            ep = prices_arr[-1] * (1 + self.slippage_pct)
            pnl_val = short_pos.pnl(ep)
            trade = Trade(
                asset=short_pos.asset, side="short",
                entry_price=short_pos.avg_entry_price, exit_price=ep,
                entry_time=short_pos.entry_time,
                exit_time=price_history[-1].get("date", datetime.now()),
                quantity=short_pos.quantity,
                pnl=pnl_val, pnl_pct=short_pos.pnl_pct(ep),
                signal_source="end_of_test",
                debate_confidence=short_pos.signal_confidence,
            )
            capital += short_pos.capital_used + pnl_val
            trades.append(trade)

        return self._build_result(
            strategy_name, asset, price_history, warmup,
            capital, trades, equity_curve, daily_returns
        )

    def _quick_atr(self, prices, period=14):
        if len(prices) < 2: return prices[-1] * 0.02
        n = min(period, len(prices)-1)
        trs = [abs(prices[i]-prices[i-1]) for i in range(len(prices)-n, len(prices))]
        return sum(trs)/len(trs) if trs else prices[-1]*0.02
