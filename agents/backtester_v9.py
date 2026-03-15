"""
WhaleTrader v9 Backtester — Asset Selection + Signal Engine
============================================================
Key change: before trading, evaluate asset quality.
Grade F assets get skipped (capital preservation).
Grade affects max position size.
"""
import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from agents.backtester import BacktestResult, Trade
from agents.signal_engine_v9 import SignalEngineV9, AssetGrade, MarketRegime
from agents.backtester_v7 import BacktesterV7, Position


class BacktesterV9(BacktesterV7):
    """
    Extends v7 backtester with asset selection layer.
    
    Before entering any trade, evaluates the asset quality.
    Grade-based allocation caps:
      A+: 95% (max conviction)
      A:  80% 
      B:  55%
      C:  35%
      F:  0%  (skip entirely)
    """
    
    async def run(self, asset: str, strategy_name: str,
                  price_history: list[dict],
                  arena=None, agents=None,
                  decision_interval: int = 1) -> BacktestResult:
        
        engine = SignalEngineV9()
        
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
        
        # Asset grade allocation caps
        GRADE_CAPS = {
            AssetGrade.A_PLUS: 0.95,
            AssetGrade.A: 0.80,
            AssetGrade.B: 0.60,
            AssetGrade.C: 0.40,
            AssetGrade.F: 0.0,
        }
        
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
            
            # ── POSITION MANAGEMENT (same as v7) ──
            if position:
                pnl_pct = position.pnl_pct(price)
                
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
                
                current_is_trend = in_trend or entered_trend
                
                if current_is_trend:
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
                    
                    if position.take_profit < price * 5:
                        position.take_profit = price * 100.0
                
                position.update_trailing(price)
                exit_reason = position.should_exit(price)
                
                max_loss = self.max_loss_per_trade
                if position.regime_at_entry in (MarketRegime.STRONG_BULL,):
                    max_loss = 0.30
                elif position.regime_at_entry in (MarketRegime.BULL,):
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
                    
                    last_sig = engine.generate_signal(
                        prices_arr[:i+1],
                        volumes_arr[:i+1] if has_volume else None,
                    )
                    if last_sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL,
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
            
            # ── ENTRY with ASSET SELECTION ──
            if position is None:
                # Evaluate asset quality every 20 bars (not every bar, for efficiency)
                if i >= 60:
                    asset_score = engine.evaluate_asset(
                        prices_arr[:i+1],
                        volumes_arr[:i+1] if has_volume else None,
                    )
                    grade_cap = GRADE_CAPS.get(asset_score.grade, 0.50)
                    
                    # Skip F-grade assets entirely
                    if asset_score.grade == AssetGrade.F:
                        continue
                else:
                    grade_cap = 0.60  # conservative before enough data
                
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
                    
                    # Apply asset grade cap
                    pos_size_pct = min(pos_size_pct, grade_cap)
                    
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
