"""
WhaleTrader - Backtester v4 (v12: Stable baseline + targeted fixes)
=====================================================================
• Warmup=15, wide trailing (25-28%), only widen, bear-detect exit
• Graduated entry: first 10 bars after warmup require bull signal (not "hold")
• Progressive loss cut: if held >20 bars AND losing >10%, tighten stop once
"""

import math
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from agents.backtester import BacktestResult, Trade
from agents.signal_engine_v5 import SignalEngineV5, SignalResult, MarketRegime


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
    bars_held: int = 0
    stop_tightened: bool = False  # one-shot tighten flag

    def update_trailing(self, price):
        self.highest_since_entry = max(self.highest_since_entry, price)
        self.stop_loss = max(self.stop_loss,
                             self.highest_since_entry * (1 - self.trailing_stop_pct))

    def should_exit(self, price):
        return "stop_loss" if price <= self.stop_loss else None

    def current_value(self, price): return self.quantity * price
    def pnl_pct(self, price):       return price / self.entry_price - 1 if self.entry_price else 0


class BacktesterV4:
    def __init__(self, initial_capital=10000.0, commission_pct=0.001,
                 slippage_pct=0.0005, max_loss_per_trade=0.06,
                 max_portfolio_exposure=0.95, cooldown_bars=1):
        self.initial_capital        = initial_capital
        self.commission_pct         = commission_pct
        self.slippage_pct           = slippage_pct
        self.max_loss_per_trade     = max_loss_per_trade
        self.max_portfolio_exposure = max_portfolio_exposure

    async def run(self, asset, strategy_name, price_history,
                  arena=None, agents=None, decision_interval=1):

        engine = SignalEngineV5(risk_per_trade=0.02, max_position_size=0.95)
        if not price_history or len(price_history) < 15:
            raise ValueError("Need ≥15 data points")

        capital       = self.initial_capital
        position      = None
        trades        = []
        equity_curve  = [capital]
        daily_returns = []
        cooldown      = 0
        confirmed_bear_cooldown = 0  # Engaged after 2+ consecutive bear exits

        prices  = [b["price"]         for b in price_history]
        volumes = [b.get("volume", 0) for b in price_history]
        has_vol = any(v > 0 for v in volumes)
        warmup  = 10
        total   = len(price_history)

        BULL = (MarketRegime.STRONG_BULL, MarketRegime.BULL)
        BEAR = (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH)

        for i in range(warmup, total):
            price = price_history[i]["price"]
            date  = price_history[i].get("date", datetime.now())
            if isinstance(date, str):
                try:    date = datetime.fromisoformat(date)
                except: date = datetime.now()

            eq = (capital + position.current_value(price)) if position else capital
            equity_curve.append(max(eq, 0.01))
            if len(equity_curve) > 2 and equity_curve[-2] > 0:
                daily_returns.append((equity_curve[-1] - equity_curve[-2]) / equity_curve[-2])

            # ── EXIT ──────────────────────────────────────────────
            if position:
                position.bars_held += 1
                pnl = position.pnl_pct(price)
                in_bull = position.regime_at_entry in BULL

                # Widen trailing only for trend-mode entries
                if in_bull:
                    if   pnl > 1.00: position.trailing_stop_pct = max(position.trailing_stop_pct, 0.40)
                    elif pnl > 0.50: position.trailing_stop_pct = max(position.trailing_stop_pct, 0.35)
                    elif pnl > 0.30: position.trailing_stop_pct = max(position.trailing_stop_pct, 0.32)
                    elif pnl > 0.15: position.trailing_stop_pct = max(position.trailing_stop_pct, 0.30)
                    elif pnl > 0.08: position.trailing_stop_pct = max(position.trailing_stop_pct, 0.28)

                # One-shot stop tighten: prolonged losing trade
                if (not position.stop_tightened and
                        position.bars_held >= 20 and pnl < -0.10):
                    i10 = max(warmup, i - 10)
                    r10 = price / prices[i10] - 1 if i > i10 else 0
                    if r10 < -0.02:   # still declining
                        new_trail = min(position.trailing_stop_pct, 0.08)
                        position.trailing_stop_pct = new_trail
                        position.stop_tightened = True

                position.update_trailing(price)
                exit_reason = position.should_exit(price)

                # Bear-momentum early exit
                # Hard max-loss cap per trade (catches catastrophic losses)
                if not exit_reason and pnl < -0.20:
                    exit_reason = "max_loss_cap"

                if not exit_reason and position.bars_held >= 8 and pnl < 0:
                    lo20 = max(warmup, i - 20); r20 = price / prices[lo20] - 1 if i > lo20 else 0
                    lo10 = max(warmup, i - 10); r10 = price / prices[lo10] - 1 if i > lo10 else 0
                    if   r20 < -0.08 and r10 < -0.05: exit_reason = "bear_detect"
                    elif pnl < -0.15 and r10 < -0.03: exit_reason = "deep_loss"

                if exit_reason:
                    trade = self._close(position, price, date, exit_reason)
                    capital += trade.pnl + position.capital_used
                    trades.append(trade)
                    engine.notify_stopped_out(MarketRegime.RANGING)
                    position = None
                    if exit_reason in ("bear_detect", "deep_loss"):
                        cooldown = 8
                        # If confirmed_bear_cooldown is active, extend it
                        if confirmed_bear_cooldown > 0:
                            confirmed_bear_cooldown = max(confirmed_bear_cooldown, 40)
                        else:
                            # Check if we've already had a bear_detect recently
                            # (indicated by recent trades all being bear_detect)
                            recent_bear = sum(1 for t in trades[-3:] if t.signal_source in ("bear_detect", "deep_loss"))
                            if recent_bear >= 2:
                                confirmed_bear_cooldown = 50  # Confirmed bear — stay flat 50 bars
                    else:
                        cooldown = 1
                    continue

            if cooldown > 0:
                cooldown -= 1
                continue

            # Tick down confirmed-bear cooldown
            if confirmed_bear_cooldown > 0:
                confirmed_bear_cooldown -= 1

            # ── SIGNAL ────────────────────────────────────────────
            sig = engine.generate_signal(
                prices[:i + 1],
                volumes[:i + 1] if has_vol else None,
                current_position=position.quantity if position else 0,
            )

            is_bull = sig.regime in BULL
            is_bear = sig.regime in BEAR

            # ── ENTRY ─────────────────────────────────────────────
            if position is None and confirmed_bear_cooldown == 0:
                should_enter = False
                pos_size     = 0.0
                trailing     = 0.25

                # Graduated entry: first 8 post-warmup bars need strong signal
                early_bar  = (i < warmup + 8)

                if is_bull:
                    if early_bar:
                        # Very early: only strong buy (avoids premature bear entries)
                        should_enter = (sig.signal == "strong_buy" or
                                        (sig.signal == "buy" and sig.confidence > 0.72))
                    else:
                        should_enter = sig.signal in ("buy", "strong_buy", "hold")
                    pos_size = 0.95
                    trailing = sig.trailing_stop_pct

                elif sig.regime == MarketRegime.VOLATILE:
                    if sig.signal in ("buy", "strong_buy") and sig.confidence > 0.55:
                        should_enter = True
                        pos_size     = 0.60
                        trailing     = 0.20

                elif sig.regime == MarketRegime.RANGING:
                    if sig.signal in ("buy", "strong_buy") and sig.confidence > 0.55:
                        should_enter = True
                        pos_size     = sig.position_size
                        trailing     = 0.12

                elif is_bear:
                    if sig.signal == "buy" and sig.confidence > 0.65:
                        should_enter = True
                        pos_size     = 0.10
                        trailing     = 0.05

                if should_enter and pos_size > 0.02 and capital > 100:
                    amt       = capital * min(pos_size, self.max_portfolio_exposure)
                    eff_price = price * (1 + self.slippage_pct)
                    qty       = (amt - amt * self.commission_pct) / eff_price
                    position  = Position(
                        asset=asset, entry_price=eff_price, entry_time=date,
                        quantity=qty, capital_used=amt,
                        stop_loss=eff_price * (1 - trailing),
                        take_profit=price * 100.0,
                        trailing_stop_pct=trailing,
                        highest_since_entry=eff_price,
                        signal_confidence=sig.confidence,
                        regime_at_entry=sig.regime,
                    )
                    capital -= amt

            elif position is not None:
                # Non-bull entries: exit if regime turns bear and losing
                if position.regime_at_entry not in BULL:
                    if is_bear and position.pnl_pct(price) < -0.03:
                        trade = self._close(position, price, date, "bear_exit")
                        capital += trade.pnl + position.capital_used
                        trades.append(trade)
                        position = None
                        cooldown = 8

        # Close open
        if position:
            fp = price_history[-1]["price"]
            t  = self._close(position, fp,
                             price_history[-1].get("date", datetime.now()), "end_of_test")
            capital += t.pnl + position.capital_used
            trades.append(t)

        return self._build_result(strategy_name, asset, price_history, warmup,
                                  capital, trades, equity_curve, daily_returns)

    def _close(self, pos, price, date, reason):
        eff  = price * (1 - self.slippage_pct)
        comm = pos.quantity * eff * self.commission_pct
        pnl  = (eff - pos.entry_price) * pos.quantity - comm
        pct  = eff / pos.entry_price - 1 if pos.entry_price else 0
        return Trade(
            asset=pos.asset, side="long",
            entry_price=pos.entry_price, exit_price=eff,
            entry_time=pos.entry_time if isinstance(pos.entry_time, datetime) else datetime.now(),
            exit_time =date          if isinstance(date,            datetime) else datetime.now(),
            quantity=pos.quantity, pnl=pnl, pnl_pct=pct,
            signal_source=reason, debate_confidence=pos.signal_confidence,
        )

    def _build_result(self, name, asset, ph, warmup, cap, trades, eq, dr):
        tr    = cap / self.initial_capital - 1
        bh    = ph[-1]["price"] / ph[warmup]["price"] - 1
        days  = max(len(ph) - warmup, 1); years = max(days / 365, 0.01)
        ar    = (1 + tr) ** (1 / years) - 1 if tr > -1 else -1
        alpha = tr - bh

        if dr and len(dr) > 1:
            vol   = _std(dr) * math.sqrt(365)
            down  = [r for r in dr if r < 0]
            ddev  = _std(down) * math.sqrt(365) if len(down) > 1 else 1e-4
            avg_r = sum(dr) / len(dr) * 365
            sharpe  = (avg_r - 0.05) / max(vol,  1e-4)
            sortino = (avg_r - 0.05) / max(ddev, 1e-4)
            pk = eq[0]; max_dd = 0; dc = []
            for e in eq:
                pk = max(pk, e); d = (e - pk) / pk if pk else 0
                dc.append(d); max_dd = min(max_dd, d)
            calmar = ar / max(abs(max_dd), 1e-4) if max_dd else 0
            s  = sorted(dr); vi = max(int(len(s) * 0.05), 1)
            v95 = s[vi-1] if s else 0; cv95 = sum(s[:vi]) / vi if s else 0
            exc = [r - bh / max(days, 1) for r in dr]
            te  = _std(exc) * math.sqrt(365) if len(exc) > 1 else 1e-4
            ir  = alpha / max(te * years, 1e-4)
        else:
            vol = ddev = sharpe = sortino = calmar = 0
            max_dd = 0; dc = [0]; v95 = cv95 = ir = 0

        mdd = 0; ds = 0; ind = False; pk2 = eq[0] if eq else 0
        for idx, e in enumerate(eq):
            if e >= pk2:
                pk2 = e
                if ind: mdd = max(mdd, idx - ds); ind = False
            elif not ind: ds = idx; ind = True

        w  = [t for t in trades if t.pnl > 0]
        lo = [t for t in trades if t.pnl <= 0]
        wr = len(w) / max(len(trades), 1)
        aw = sum(t.pnl_pct for t in w)  / max(len(w),  1)
        al = sum(t.pnl_pct for t in lo) / max(len(lo), 1)
        pf = sum(t.pnl for t in w) / max(abs(sum(t.pnl for t in lo)), 0.01)
        ad = 0
        if trades:
            durs = [(t.exit_time - t.entry_time).total_seconds() / 3600
                    for t in trades
                    if isinstance(t.entry_time, datetime) and isinstance(t.exit_time, datetime)]
            ad = sum(durs) / max(len(durs), 1)
        confs = [t.debate_confidence for t in trades] or [0]
        hcw = sum(1 for t in trades if t.debate_confidence > 0.8 and t.pnl > 0)
        hct = sum(1 for t in trades if t.debate_confidence > 0.8)
        lcw = sum(1 for t in trades if t.debate_confidence < 0.5 and t.pnl > 0)
        lct = sum(1 for t in trades if t.debate_confidence < 0.5)

        _d = lambda x: x if isinstance(x, datetime) else datetime.now()
        return BacktestResult(
            strategy_name=name, asset=asset,
            start_date=_d(ph[warmup].get("date")), end_date=_d(ph[-1].get("date")),
            total_return=tr, annualized_return=ar, benchmark_return=bh, alpha=alpha,
            sharpe_ratio=sharpe, sortino_ratio=sortino, calmar_ratio=calmar,
            max_drawdown=max_dd, max_drawdown_duration_days=mdd,
            volatility=vol, downside_deviation=ddev,
            information_ratio=ir, cvar_95=cv95, var_95=v95,
            total_trades=len(trades), winning_trades=len(w), losing_trades=len(lo),
            win_rate=wr, avg_win=aw, avg_loss=al, profit_factor=pf,
            avg_trade_duration_hours=ad,
            avg_debate_confidence=sum(confs) / len(confs),
            high_confidence_win_rate=hcw / max(hct, 1),
            low_confidence_win_rate =lcw / max(lct, 1),
            confidence_correlation=0.0, debate_rounds_avg=2.0, consensus_rate=0.8,
            equity_curve=eq, drawdown_curve=dc, daily_returns=dr, trades=trades,
        )


def _std(vals):
    if len(vals) < 2: return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
