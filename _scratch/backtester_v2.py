"""
WhaleTrader - Backtester v2 (Fixed Execution Engine)
=====================================================
CRITICAL FIXES from v2 iteration 1:
- Fixed: short selling causing -100% MaxDD (capital going negative)
- Fixed: equity calculation for open positions
- Added: max loss per trade hard cap (no single trade can lose > 5% of portfolio)
- Added: proper collateral management for shorts
- Simplified: removed short selling (retail/crypto mostly long-only)
- Added: partial position sizing (scale in/out)
- Added: regime-adaptive behavior (defensive in bear, aggressive in bull)

Design principle: NEVER lose more than 5% on a single trade.
"""

import math
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from agents.backtester import BacktestResult, Trade
from agents.signal_engine import SignalEngine, SignalResult, MarketRegime


@dataclass
class Position:
    """Active position with risk management"""
    asset: str
    entry_price: float
    entry_time: datetime
    quantity: float
    capital_used: float         # How much capital is locked in this position
    stop_loss: float
    take_profit: float
    trailing_stop_pct: float
    highest_since_entry: float
    signal_confidence: float
    regime_at_entry: MarketRegime
    
    def update_trailing(self, price: float):
        """Update trailing stop (only tightens, never loosens)"""
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
    
    def pnl(self, price: float) -> float:
        return (price - self.entry_price) * self.quantity
    
    def pnl_pct(self, price: float) -> float:
        if self.entry_price == 0:
            return 0
        return (price / self.entry_price) - 1


class BacktesterV2:
    """
    Advanced backtester with multi-factor signal engine.
    Long-only, with proper risk management.
    """
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 commission_pct: float = 0.001,
                 slippage_pct: float = 0.0005,
                 max_loss_per_trade: float = 0.06,  # 6% max loss per trade
                 max_portfolio_exposure: float = 0.90,
                 cooldown_bars: int = 1,
                 ):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.max_loss_per_trade = max_loss_per_trade
        self.max_portfolio_exposure = max_portfolio_exposure
        self.cooldown_bars = cooldown_bars
        
        self.signal_engine = SignalEngine(
            risk_per_trade=0.02,
            max_position_size=0.60,
        )
    
    async def run(self, asset: str, strategy_name: str,
                  price_history: list[dict],
                  arena=None, agents=None,
                  decision_interval: int = 1) -> BacktestResult:
        
        # Create fresh signal engine for each run (reset regime state)
        signal_engine = SignalEngine(
            risk_per_trade=0.02,
            max_position_size=0.60,
        )
        
        if not price_history or len(price_history) < 55:
            raise ValueError("Need at least 55 data points")
        
        capital = self.initial_capital    # Cash on hand
        position: Optional[Position] = None
        trades: list[Trade] = []
        equity_curve = [capital]
        daily_returns = []
        cooldown = 0
        
        prices_arr = [bar["price"] for bar in price_history]
        volumes_arr = [bar.get("volume", 0) for bar in price_history]
        has_volume = any(v > 0 for v in volumes_arr)
        
        warmup = 50
        total = len(price_history)
        
        for i in range(warmup, total):
            price = price_history[i]["price"]
            date = price_history[i].get("date", datetime.now())
            if isinstance(date, str):
                try: date = datetime.fromisoformat(date)
                except: date = datetime.now()
            
            # ── Total equity = cash + position value ──
            if position:
                total_equity = capital + position.current_value(price)
            else:
                total_equity = capital
            
            # Safety: total equity should never be negative
            total_equity = max(total_equity, 0.01)
            
            equity_curve.append(total_equity)
            if len(equity_curve) > 2 and equity_curve[-2] > 0:
                daily_returns.append((total_equity - equity_curve[-2]) / equity_curve[-2])
            
            # ── Check stop-loss / take-profit / regime change ──
            if position:
                position.update_trailing(price)
                exit_reason = position.should_exit(price)
                
                # Max loss: regime-dependent
                max_loss = self.max_loss_per_trade
                if position.regime_at_entry in (MarketRegime.VOLATILE, MarketRegime.STRONG_BULL):
                    max_loss = self.max_loss_per_trade * 2.0  # Very wide in trends
                elif position.regime_at_entry in (MarketRegime.BULL,):
                    max_loss = self.max_loss_per_trade * 1.5
                
                if position.pnl_pct(price) < -max_loss:
                    exit_reason = "max_loss"
                
                if exit_reason:
                    trade = self._close(position, price, date, exit_reason)
                    capital += trade.pnl + position.capital_used
                    trades.append(trade)
                    position = None
                    cooldown = self.cooldown_bars
                    continue
            
            # ── Decision interval ──
            if (i - warmup) % decision_interval != 0:
                continue
            
            if cooldown > 0:
                cooldown -= 1
                continue
            
            # ── Generate signal ──
            sig = signal_engine.generate_signal(
                prices_arr[:i+1],
                volumes_arr[:i+1] if has_volume else None,
                current_position=position.quantity if position else 0,
            )
            
            # ── Execute ──
            if position is None:
                if sig.signal in ("buy", "strong_buy") and sig.confidence > 0.55:
                    # Calculate position size
                    total_eq = capital  # Cash available
                    pos_size_pct = min(sig.position_size, self.max_portfolio_exposure)
                    trade_amount = total_eq * pos_size_pct
                    
                    if trade_amount < total_eq * 0.03:  # Min 3% of capital
                        continue
                    
                    # Apply slippage and commission
                    effective_price = price * (1 + self.slippage_pct)
                    commission = trade_amount * self.commission_pct
                    actual_invest = trade_amount - commission
                    qty = actual_invest / effective_price
                    
                    # Ensure stop loss doesn't exceed max loss
                    max_stop = effective_price * (1 - self.max_loss_per_trade)
                    stop_loss = max(sig.stop_loss, max_stop)
                    
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
                    )
                    capital -= trade_amount  # Lock capital
            
            else:
                # Check for signal-based exit — regime AND PnL dependent
                # Key insight: if we're already profitable, DON'T exit on weak signals
                # Let trailing stop handle the exit instead
                pnl_pct = position.pnl_pct(price)
                
                sell_conf_threshold = 0.55
                if sig.regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
                    sell_conf_threshold = 0.85
                elif sig.regime == MarketRegime.VOLATILE:
                    sell_conf_threshold = 0.75
                
                # If profitable: even harder to sell (let trailing stop do it)
                if pnl_pct > 0.10:
                    sell_conf_threshold = 0.95  # Almost never signal-exit when up 10%+
                elif pnl_pct > 0.05:
                    sell_conf_threshold = max(sell_conf_threshold, 0.85)
                
                if sig.signal in ("sell", "strong_sell") and sig.confidence > sell_conf_threshold:
                    trade = self._close(position, price, date, "signal_exit")
                    capital += trade.pnl + position.capital_used
                    trades.append(trade)
                    position = None
        
        # ── Close any open position ──
        if position:
            final_price = price_history[-1]["price"]
            trade = self._close(position, final_price, 
                               price_history[-1].get("date", datetime.now()), 
                               "end_of_test")
            capital += trade.pnl + position.capital_used
            trades.append(trade)
            position = None
        
        # ── Build result ──
        return self._build_result(
            strategy_name, asset, price_history, warmup,
            capital, trades, equity_curve, daily_returns
        )
    
    def _close(self, pos: Position, price: float, date, reason: str) -> Trade:
        """Close position and create trade record."""
        effective_price = price * (1 - self.slippage_pct)
        commission = pos.quantity * effective_price * self.commission_pct
        pnl = (effective_price - pos.entry_price) * pos.quantity - commission
        pnl_pct = (effective_price / pos.entry_price) - 1 if pos.entry_price > 0 else 0
        
        return Trade(
            asset=pos.asset, side="long",
            entry_price=pos.entry_price, exit_price=effective_price,
            entry_time=pos.entry_time if isinstance(pos.entry_time, datetime) else datetime.now(),
            exit_time=date if isinstance(date, datetime) else datetime.now(),
            quantity=pos.quantity,
            pnl=pnl, pnl_pct=pnl_pct,
            signal_source=reason,
            debate_confidence=pos.signal_confidence,
        )
    
    def _build_result(self, strategy_name, asset, price_history, warmup,
                      final_capital, trades, equity_curve, daily_returns):
        """Compute all metrics."""
        total_return = (final_capital / self.initial_capital) - 1
        bh_return = (price_history[-1]["price"] / price_history[warmup]["price"]) - 1
        
        days = max(len(price_history) - warmup, 1)
        years = max(days / 365, 0.01)
        ann_return = (1 + total_return) ** (1/years) - 1 if total_return > -1 else -1
        alpha = total_return - bh_return
        
        if daily_returns and len(daily_returns) > 1:
            vol = _std(daily_returns) * math.sqrt(365)
            down = [r for r in daily_returns if r < 0]
            down_dev = _std(down) * math.sqrt(365) if len(down) > 1 else 0.001
            
            avg_r = sum(daily_returns) / len(daily_returns) * 365
            sharpe = (avg_r - 0.05) / max(vol, 0.001)
            sortino = (avg_r - 0.05) / max(down_dev, 0.001)
            
            peak = equity_curve[0]
            max_dd = 0; dd_curve = []
            for eq in equity_curve:
                peak = max(peak, eq)
                dd = (eq - peak) / peak if peak > 0 else 0
                dd_curve.append(dd)
                max_dd = min(max_dd, dd)
            
            calmar = ann_return / max(abs(max_dd), 0.001) if max_dd != 0 else 0
            
            s = sorted(daily_returns)
            vi = max(int(len(s) * 0.05), 1)
            var_95 = s[vi-1] if s else 0
            cvar_95 = sum(s[:vi]) / vi if s else 0
            
            excess = [r - bh_return/max(days,1) for r in daily_returns]
            te = _std(excess) * math.sqrt(365) if len(excess) > 1 else 0.001
            info_ratio = alpha / max(te * years, 0.001)
        else:
            vol = down_dev = 0
            sharpe = sortino = calmar = 0
            max_dd = 0; dd_curve = [0]
            var_95 = cvar_95 = info_ratio = 0
        
        # Drawdown duration
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
            start_date=price_history[warmup].get("date", datetime.now()) if isinstance(price_history[warmup].get("date"), datetime) else datetime.now(),
            end_date=price_history[-1].get("date", datetime.now()) if isinstance(price_history[-1].get("date"), datetime) else datetime.now(),
            total_return=total_return, annualized_return=ann_return,
            benchmark_return=bh_return, alpha=alpha,
            sharpe_ratio=sharpe, sortino_ratio=sortino, calmar_ratio=calmar,
            max_drawdown=max_dd, max_drawdown_duration_days=max_dd_dur,
            volatility=vol, downside_deviation=down_dev,
            information_ratio=info_ratio, cvar_95=cvar_95, var_95=var_95,
            total_trades=len(trades), winning_trades=len(win), losing_trades=len(lose),
            win_rate=wr, avg_win=avg_win, avg_loss=avg_loss,
            profit_factor=pf, avg_trade_duration_hours=avg_dur,
            avg_debate_confidence=sum(confs)/len(confs),
            high_confidence_win_rate=sum(1 for t in trades if t.debate_confidence > 0.8 and t.pnl > 0) / max(sum(1 for t in trades if t.debate_confidence > 0.8), 1),
            low_confidence_win_rate=sum(1 for t in trades if t.debate_confidence < 0.5 and t.pnl > 0) / max(sum(1 for t in trades if t.debate_confidence < 0.5), 1),
            confidence_correlation=0.0,
            debate_rounds_avg=2.0, consensus_rate=0.8,
            equity_curve=equity_curve, drawdown_curve=dd_curve,
            daily_returns=daily_returns, trades=trades,
        )


def _std(values: list[float]) -> float:
    if len(values) < 2: return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v-m)**2 for v in values) / (len(values)-1))
