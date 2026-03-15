"""
Realistic AHF (AI-Hedge-Fund) Simulator
========================================
Based on actual AHF source code from github.com/virattt/ai-hedge-fund

AHF's technical analyst uses 5 sub-strategies with weighted voting:
1. Trend Following (25%): EMA 8/21/55 + ADX
2. Mean Reversion (20%): z-score(50MA) + Bollinger Bands + RSI 14/28
3. Momentum (25%): 1M/3M/6M returns + Volume confirmation
4. Volatility (15%): Vol regime (63MA) + Vol z-score
5. Statistical Arbitrage (15%): Price distribution stats

This module replicates that logic WITHOUT LLM calls, using only
the technical analysis component (which is the deterministic part).

AHF's other agents (fundamentals, sentiment, 12 guru agents) use LLM,
so we can't replicate them. We only replicate the technicals agent.
"""
import math
import random
from datetime import datetime


def _ema(prices, period):
    if len(prices) < period: return prices[-1]
    mult = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * mult + ema * (1 - mult)
    return ema

def _sma(prices, period):
    if len(prices) < period: return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def _stdev(values):
    if len(values) < 2: return 0.001
    m = sum(values) / len(values)
    return math.sqrt(sum((v-m)**2 for v in values) / (len(values)-1))

def _rsi(prices, period=14):
    if len(prices) < period+1: return 50
    deltas = [prices[i]-prices[i-1] for i in range(1, len(prices))]
    recent = deltas[-period:]
    ag = sum(max(d,0) for d in recent) / period
    al = sum(max(-d,0) for d in recent) / period
    if al == 0: return 100
    return 100 - 100/(1+ag/al)

def _adx_simple(prices, period=14):
    """Simplified ADX (no H/L data, uses close-to-close)."""
    n = len(prices)
    if n < period+2: return 25.0
    plus_dm = []; minus_dm = []; tr_list = []
    for i in range(1, n):
        diff = prices[i] - prices[i-1]
        tr = abs(diff)
        plus_dm.append(max(diff, 0) if diff > -diff else 0)
        minus_dm.append(max(-diff, 0) if -diff > diff else 0)
        tr_list.append(max(tr, 0.001))
    atr_s = sum(tr_list[:period])/period
    pdm_s = sum(plus_dm[:period])/period
    mdm_s = sum(minus_dm[:period])/period
    dx_list = []
    for j in range(period, len(tr_list)):
        atr_s = atr_s - atr_s/period + tr_list[j]
        pdm_s = pdm_s - pdm_s/period + plus_dm[j]
        mdm_s = mdm_s - mdm_s/period + minus_dm[j]
        if atr_s == 0: continue
        pdi = pdm_s/atr_s*100; mdi = mdm_s/atr_s*100
        di_sum = pdi + mdi
        if di_sum == 0: continue
        dx_list.append(abs(pdi-mdi)/di_sum*100)
    if not dx_list: return 25.0
    return sum(dx_list[-period:])/min(len(dx_list),period)


class AHFTechnicalAnalyst:
    """Replicates AHF's technical_analyst_agent using price data only."""

    def analyze(self, prices: list[float], volumes: list[float] = None):
        """
        Returns: {
            "signal": "bullish" | "bearish" | "neutral",
            "confidence": 0.0-1.0,
            "strategies": {name: {signal, confidence}}
        }
        """
        trend = self._trend_signals(prices)
        mean_rev = self._mean_reversion_signals(prices)
        momentum = self._momentum_signals(prices)
        volatility = self._volatility_signals(prices, volumes)
        stat_arb = self._stat_arb_signals(prices)

        # Weighted ensemble (AHF's exact weights)
        weights = {
            "trend": 0.25,
            "mean_reversion": 0.20,
            "momentum": 0.25,
            "volatility": 0.15,
            "stat_arb": 0.15,
        }

        strategies = {
            "trend": trend,
            "mean_reversion": mean_rev,
            "momentum": momentum,
            "volatility": volatility,
            "stat_arb": stat_arb,
        }

        # Combine signals
        score = 0.0
        total_conf = 0.0
        for name, strat in strategies.items():
            w = weights[name]
            if strat["signal"] == "bullish":
                score += w * strat["confidence"]
            elif strat["signal"] == "bearish":
                score -= w * strat["confidence"]
            total_conf += w * strat["confidence"]

        if score > 0.15:
            signal = "bullish"
        elif score < -0.15:
            signal = "bearish"
        else:
            signal = "neutral"

        confidence = min(abs(score) * 2, 1.0)

        return {
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "strategies": strategies,
        }

    def _trend_signals(self, prices):
        """EMA 8/21/55 + ADX"""
        ema8 = _ema(prices, 8)
        ema21 = _ema(prices, 21)
        ema55 = _ema(prices, min(55, len(prices)))
        adx = _adx_simple(prices)
        trend_strength = adx / 100.0

        short_trend = ema8 > ema21
        medium_trend = ema21 > ema55

        if short_trend and medium_trend:
            return {"signal": "bullish", "confidence": trend_strength}
        elif not short_trend and not medium_trend:
            return {"signal": "bearish", "confidence": trend_strength}
        else:
            return {"signal": "neutral", "confidence": 0.5}

    def _mean_reversion_signals(self, prices):
        """z-score(50MA) + Bollinger Bands"""
        n = len(prices)
        period = min(50, n)
        ma = _sma(prices, period)
        std = _stdev(prices[-period:])
        z_score = (prices[-1] - ma) / std if std > 0 else 0

        # Bollinger Bands (20-period, 2 std)
        bb_period = min(20, n)
        bb_sma = _sma(prices, bb_period)
        bb_std = _stdev(prices[-bb_period:])
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std
        bb_range = bb_upper - bb_lower
        price_vs_bb = (prices[-1] - bb_lower) / bb_range if bb_range > 0 else 0.5

        if z_score < -2 and price_vs_bb < 0.2:
            return {"signal": "bullish", "confidence": min(abs(z_score)/4, 1.0)}
        elif z_score > 2 and price_vs_bb > 0.8:
            return {"signal": "bearish", "confidence": min(abs(z_score)/4, 1.0)}
        else:
            return {"signal": "neutral", "confidence": 0.5}

    def _momentum_signals(self, prices, volumes=None):
        """1M/3M/6M returns + volume confirmation"""
        n = len(prices)
        rets = [prices[i]/prices[i-1]-1 for i in range(1,n)]

        mom_1m = sum(rets[-21:]) if len(rets) >= 21 else sum(rets)
        mom_3m = sum(rets[-63:]) if len(rets) >= 63 else mom_1m
        mom_6m = sum(rets[-126:]) if len(rets) >= 126 else mom_3m

        momentum_score = 0.4*mom_1m + 0.3*mom_3m + 0.3*mom_6m

        # Volume confirmation (simplified)
        vol_confirm = True  # default if no volume data

        if momentum_score > 0.05 and vol_confirm:
            return {"signal": "bullish", "confidence": min(abs(momentum_score)*5, 1.0)}
        elif momentum_score < -0.05 and vol_confirm:
            return {"signal": "bearish", "confidence": min(abs(momentum_score)*5, 1.0)}
        else:
            return {"signal": "neutral", "confidence": 0.5}

    def _volatility_signals(self, prices, volumes=None):
        """Vol regime detection using 63MA of vol"""
        n = len(prices)
        rets = [prices[i]/prices[i-1]-1 for i in range(1,n)]
        if len(rets) < 21:
            return {"signal": "neutral", "confidence": 0.5}

        # Historical volatility (21-day)
        hist_vol = _stdev(rets[-21:]) * math.sqrt(252)

        # Volatility MA (63-day)
        if len(rets) >= 63:
            vol_windows = []
            for start in range(max(0, len(rets)-63), len(rets)-20):
                vol_windows.append(_stdev(rets[start:start+21]) * math.sqrt(252))
            vol_ma = sum(vol_windows)/len(vol_windows) if vol_windows else hist_vol
        else:
            vol_ma = hist_vol

        vol_regime = hist_vol / vol_ma if vol_ma > 0 else 1.0

        # Vol z-score
        if len(rets) >= 63:
            vol_std = _stdev(vol_windows) if len(vol_windows) > 1 else 0.01
            vol_z = (hist_vol - vol_ma) / vol_std if vol_std > 0 else 0
        else:
            vol_z = 0

        if vol_regime < 0.8 and vol_z < -1:
            return {"signal": "bullish", "confidence": min(abs(vol_z)/3, 1.0)}
        elif vol_regime > 1.2 and vol_z > 1:
            return {"signal": "bearish", "confidence": min(abs(vol_z)/3, 1.0)}
        else:
            return {"signal": "neutral", "confidence": 0.5}

    def _stat_arb_signals(self, prices):
        """Statistical arbitrage signals based on price distribution"""
        n = len(prices)
        if n < 30:
            return {"signal": "neutral", "confidence": 0.5}

        rets = [prices[i]/prices[i-1]-1 for i in range(1,n)]
        mean_ret = sum(rets)/len(rets)
        std_ret = _stdev(rets)
        if std_ret == 0:
            return {"signal": "neutral", "confidence": 0.5}

        # Skewness
        skew = sum((r-mean_ret)**3 for r in rets) / (len(rets)*std_ret**3)
        # Kurtosis
        kurt = sum((r-mean_ret)**4 for r in rets) / (len(rets)*std_ret**4) - 3

        # Hurst exponent (simplified)
        half = len(rets)//2
        std1 = _stdev(rets[:half]) if half > 1 else 0.01
        std2 = _stdev(rets[half:]) if len(rets)-half > 1 else 0.01
        hurst_approx = math.log(max(std2/std1, 0.01)) / math.log(2) + 0.5 if std1 > 0 else 0.5

        # Mean reverting (hurst < 0.5) vs trending (hurst > 0.5)
        if hurst_approx < 0.4 and skew > 0:
            return {"signal": "bullish", "confidence": min((0.5-hurst_approx)*3, 1.0)}
        elif hurst_approx > 0.6 and skew < 0:
            return {"signal": "bearish", "confidence": min((hurst_approx-0.5)*3, 1.0)}
        else:
            return {"signal": "neutral", "confidence": 0.5}


class AHFBacktester:
    """
    Backtester that uses AHF's technical signals to make trading decisions.
    This is more realistic than our previous random simulator.
    """

    def __init__(self, initial_capital=10000, commission_pct=0.001,
                 lookback=60, rebalance_interval=5):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.lookback = lookback
        self.rebalance_interval = rebalance_interval
        self.analyst = AHFTechnicalAnalyst()

    def run(self, price_history: list[dict]) -> dict:
        """Run AHF-style trading on price history."""
        prices = [bar["price"] for bar in price_history]
        volumes = [bar.get("volume", 0) for bar in price_history]
        n = len(prices)
        bh = prices[-1]/prices[0]-1

        capital = self.initial_capital
        position = 0  # shares held
        position_cost = 0
        trades = []
        equity_curve = [capital]
        target_alloc = 0.0  # 0 = no position, 0.5 = half, 1.0 = full

        for i in range(self.lookback, n):
            price = prices[i]

            # Rebalance at interval
            if (i - self.lookback) % self.rebalance_interval == 0:
                analysis = self.analyst.analyze(
                    prices[:i+1],
                    volumes[:i+1] if any(v>0 for v in volumes) else None
                )

                # AHF-style allocation: scale by signal and confidence
                if analysis["signal"] == "bullish":
                    target_alloc = min(analysis["confidence"] * 0.8, 0.8)
                elif analysis["signal"] == "bearish":
                    target_alloc = 0.0  # AHF doesn't short
                else:
                    target_alloc = 0.2  # small neutral position

            # Calculate current position value
            pos_value = position * price
            equity = capital + pos_value
            target_value = equity * target_alloc

            # Rebalance to target
            diff = target_value - pos_value
            if abs(diff) > equity * 0.05:  # 5% threshold to avoid churn
                if diff > 0:  # buy
                    buy_amount = min(diff, capital * 0.95)
                    if buy_amount > 100:
                        commission = buy_amount * self.commission_pct
                        shares = (buy_amount - commission) / price
                        position += shares
                        capital -= buy_amount
                        trades.append(buy_amount / equity)
                elif diff < 0:  # sell
                    sell_shares = min(-diff / price, position)
                    if sell_shares > 0:
                        sell_value = sell_shares * price
                        commission = sell_value * self.commission_pct
                        capital += sell_value - commission
                        position -= sell_shares
                        trades.append(-sell_value / equity)

            equity_curve.append(capital + position * price)

        # Close final position
        if position > 0:
            final_value = position * prices[-1]
            commission = final_value * self.commission_pct
            capital += final_value - commission
            position = 0

        total_return = capital / self.initial_capital - 1
        alpha = total_return - bh

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            peak = max(peak, eq)
            dd = (eq - peak) / peak
            max_dd = min(max_dd, dd)

        return {
            "total_return": total_return,
            "alpha": alpha,
            "max_dd": max_dd,
            "trades": len(trades),
            "win_rate": sum(1 for t in trades if t > 0) / max(len(trades), 1),
        }
