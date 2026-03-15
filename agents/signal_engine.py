"""
WhaleTrader - Signal Engine v4: Adaptive Regime Engine
========================================================
FUNDAMENTAL REDESIGN based on 6 rounds of iteration.

Core insight: ONE strategy cannot win all regimes.
Solution: THREE sub-strategies, each optimized for its regime.

1. TREND RIDER (Bull/Strong Bull): 
   - Buy breakouts, NEVER take profit, only trailing stop
   - Wide stops, large positions, infrequent trades
   - "Let winners run" — like Turtle Traders & Warren Buffett
   
2. MEAN REVERTER (Ranging/Sideways):
   - Buy oversold (RSI<30, below Bollinger), sell overbought
   - Tight stops, small positions, frequent trades
   - Profit from oscillation — like market makers

3. CRISIS ALPHA (Bear/Crash):
   - Stay mostly cash, only buy extreme oversold bounces
   - Very small positions, very tight stops
   - Capital preservation is #1 — like Ray Dalio's All Weather

The engine auto-detects regime and switches strategy.

Academic basis:
- Regime switching: Hamilton (1989) Markov-switching models
- Turtle Trading: Richard Dennis (1983)
- Mean reversion: Poterba & Summers (1988)
- Crisis alpha: Nassim Taleb's antifragile
- Adaptive markets: Andrew Lo (2004)
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MarketRegime(Enum):
    STRONG_BULL = "strong_bull"
    BULL = "bull"
    RANGING = "ranging"
    VOLATILE = "volatile"
    BEAR = "bear"
    STRONG_BEAR = "strong_bear"
    CRASH = "crash"


@dataclass
class SignalResult:
    signal: str              # buy/strong_buy/sell/strong_sell/hold
    confidence: float        # 0-1
    regime: MarketRegime
    position_size: float     # fraction of capital
    stop_loss: float         # absolute price
    take_profit: float       # absolute price
    trailing_stop_pct: float # as fraction (0.05 = 5%)
    factors: dict
    reasoning: str


class SignalEngine:
    """
    Adaptive multi-regime signal engine v4.
    Automatically switches between trend-following, mean-reversion,
    and crisis-alpha based on detected market regime.
    """
    
    def __init__(self,
                 risk_per_trade: float = 0.02,
                 max_position_size: float = 0.60,
                 atr_period: int = 14,
                 donchian_period: int = 20,
                 ):
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self.atr_period = atr_period
        self.donchian_period = donchian_period
        self._prev_regime = None  # Regime inertia
        self._regime_hold_count = 0
    
    def generate_signal(self, prices: list[float],
                        volumes: list[float] = None,
                        current_position: float = 0) -> SignalResult:
        if len(prices) < 55:
            return SignalResult("hold", 0.3, MarketRegime.RANGING, 0, 0, 0, 0.05, {}, "warmup")
        
        price = prices[-1]
        atr = _atr(prices, self.atr_period)
        
        # ── STEP 1: Regime Detection with INERTIA ──
        raw_regime, regime_conf = self._detect_regime_v2(prices)
        regime = self._apply_regime_inertia(raw_regime, regime_conf)
        
        # ── STEP 2: Route to appropriate sub-strategy ──
        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            return self._trend_rider(prices, volumes, price, atr, regime, regime_conf, current_position)
        elif regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH):
            return self._crisis_alpha(prices, volumes, price, atr, regime, regime_conf, current_position)
        elif regime == MarketRegime.VOLATILE:
            # Volatile can be up OR down — check direction
            ret_20 = (prices[-1] / prices[-20] - 1) if len(prices) >= 20 else 0
            if ret_20 > 0.03:
                return self._trend_rider(prices, volumes, price, atr, regime, regime_conf, current_position)
            elif ret_20 < -0.03:
                return self._crisis_alpha(prices, volumes, price, atr, regime, regime_conf, current_position)
            else:
                return self._mean_reverter(prices, volumes, price, atr, regime, regime_conf, current_position)
        else:  # RANGING
            return self._mean_reverter(prices, volumes, price, atr, regime, regime_conf, current_position)
    
    # ═══════════════════════════════════════════════════════
    # SUB-STRATEGY 1: TREND RIDER (Bull markets)
    # ═══════════════════════════════════════════════════════
    
    def _trend_rider(self, prices, volumes, price, atr, regime, regime_conf, cur_pos):
        """
        Trend-following strategy for bull markets.
        Key principles:
        - Buy on pullbacks within uptrend (not at peaks)
        - Wide trailing stops (ride the trend)
        - NO take profit (let winners run indefinitely)
        - Large positions when trend is strong
        """
        factors = {}
        
        # 1. Trend strength: EMA alignment (8 > 21 > 50)
        ema8 = _ema_val(prices, 8)
        ema21 = _ema_val(prices, 21)
        ema50 = _ema_val(prices, 50) if len(prices) >= 50 else ema21
        
        aligned = (ema8 > ema21 > ema50)  # Perfect bull alignment
        
        ema_score = 0
        if ema21 > 0:
            ema_score += _clamp((ema8/ema21 - 1) * 30, -1, 1) * 0.4
            ema_score += _clamp((ema21/ema50 - 1) * 20, -1, 1) * 0.3
            ema_score += _clamp((price/ema21 - 1) * 15, -1, 1) * 0.3
        factors["ema_alignment"] = ema_score
        
        # 2. Pullback detection: price near EMA21 in uptrend = buy the dip
        if aligned and ema21 > 0:
            dist_from_ema = (price - ema21) / ema21
            if -0.03 < dist_from_ema < 0.01:
                # Price pulled back to EMA — prime buy zone
                factors["pullback"] = 0.8
            elif dist_from_ema < -0.05:
                # Too far below — trend might be broken
                factors["pullback"] = -0.3
            elif dist_from_ema > 0.08:
                # Extended above — don't chase
                factors["pullback"] = -0.2
            else:
                factors["pullback"] = 0.3
        else:
            factors["pullback"] = 0.0
        
        # 3. Donchian breakout
        factors["donchian"] = self._donchian_signal(prices)
        
        # 4. MACD momentum (is trend accelerating?)
        factors["macd"] = self._macd_momentum(prices)
        
        # 5. Volume confirmation
        factors["volume"] = self._volume_confirm(prices, volumes)
        
        # Composite — weight toward EMA + pullback
        score = (
            factors["ema_alignment"] * 0.30 +
            factors["pullback"] * 0.25 +
            factors["donchian"] * 0.25 +
            factors["macd"] * 0.10 +
            factors["volume"] * 0.10
        )
        
        # In strong bull, lower the buy threshold (be more aggressive)
        if regime == MarketRegime.STRONG_BULL:
            buy_threshold = 0.10
            sell_threshold = -0.30  # Very reluctant to sell in strong bull
        else:
            buy_threshold = 0.15
            sell_threshold = -0.20
        
        if score > buy_threshold:
            signal = "strong_buy" if score > 0.30 else "buy"
        elif score < sell_threshold:
            signal = "sell"
        else:
            signal = "hold"
        
        confidence = min(0.50 + abs(score) * 1.5, 0.95)
        
        # Position sizing: LARGE in bull (trend is your friend)
        pos_size = self._trend_position_size(price, atr, confidence, regime)
        
        # Stops: WIDE — let the trend breathe
        stop_loss, take_profit, trailing_pct = self._trend_stops(prices, price, atr, regime)
        
        reasoning = (f"TREND_RIDER regime={regime.value} score={score:+.3f} "
                    f"ema={factors['ema_alignment']:+.2f} pb={factors['pullback']:+.2f} "
                    f"donch={factors['donchian']:+.2f}")
        
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                          take_profit, trailing_pct, factors, reasoning)
    
    # ═══════════════════════════════════════════════════════
    # SUB-STRATEGY 2: MEAN REVERTER (Ranging/Sideways)
    # ═══════════════════════════════════════════════════════
    
    def _mean_reverter(self, prices, volumes, price, atr, regime, regime_conf, cur_pos):
        """
        Mean reversion strategy for sideways markets.
        Key principles:
        - Buy at lower Bollinger, sell at upper
        - RSI extremes (< 30 buy, > 70 sell)
        - TIGHT stops and take-profits (no trends to ride)
        - Small positions (no strong edge)
        """
        factors = {}
        
        # 1. Bollinger Band position
        sma20 = sum(prices[-20:]) / 20
        std20 = _stdev_s(prices[-20:])
        if std20 > 0:
            z = (price - sma20) / std20
            factors["bollinger"] = _clamp(-z / 2.0, -1, 1)
        else:
            factors["bollinger"] = 0
        
        # 2. RSI
        rsi = _rsi(prices, 14)
        if rsi is not None:
            if rsi < 25: factors["rsi"] = 0.9
            elif rsi < 35: factors["rsi"] = 0.5
            elif rsi < 45: factors["rsi"] = 0.2
            elif rsi > 75: factors["rsi"] = -0.9
            elif rsi > 65: factors["rsi"] = -0.5
            elif rsi > 55: factors["rsi"] = -0.2
            else: factors["rsi"] = 0
        else:
            factors["rsi"] = 0
        
        # 3. Price vs SMA — distance from mean
        if sma20 > 0:
            factors["mean_dist"] = _clamp((sma20 - price) / sma20 * 15, -1, 1)
        else:
            factors["mean_dist"] = 0
        
        # 4. Stochastic oscillator approximation
        if len(prices) >= 14:
            h14 = max(prices[-14:]); l14 = min(prices[-14:])
            if h14 != l14:
                k = (price - l14) / (h14 - l14)
                factors["stoch"] = _clamp((0.5 - k) * 2, -1, 1)
            else:
                factors["stoch"] = 0
        else:
            factors["stoch"] = 0
        
        factors["volume"] = self._volume_confirm(prices, volumes)
        
        score = (
            factors["bollinger"] * 0.30 +
            factors["rsi"] * 0.30 +
            factors["mean_dist"] * 0.15 +
            factors["stoch"] * 0.15 +
            factors["volume"] * 0.10
        )
        
        # Higher threshold — only trade clear extremes
        if score > 0.25:
            signal = "strong_buy" if score > 0.45 else "buy"
        elif score < -0.25:
            signal = "strong_sell" if score < -0.45 else "sell"
        else:
            signal = "hold"
        
        confidence = min(0.40 + abs(score) * 1.2, 0.90)
        
        # Position sizing: SMALL (no strong edge in ranging)
        pos_size = min(self.risk_per_trade / max((atr * 1.5) / price, 0.005), 0.25)
        pos_size *= confidence * 0.8
        pos_size = _clamp(pos_size, 0.05, 0.25)
        
        # Stops: TIGHT (mean reversion has defined risk)
        stop_loss = price - atr * 1.5
        stop_loss = max(stop_loss, price * 0.94)  # Max 6% stop
        risk = price - stop_loss
        take_profit = price + risk * 2.0  # 2:1 R:R (take profit IS appropriate here)
        trailing_pct = atr * 1.5 / price
        
        reasoning = (f"MEAN_REVERTER regime={regime.value} score={score:+.3f} "
                    f"bb={factors['bollinger']:+.2f} rsi={factors['rsi']:+.2f}")
        
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                          take_profit, trailing_pct, factors, reasoning)
    
    # ═══════════════════════════════════════════════════════
    # SUB-STRATEGY 3: CRISIS ALPHA (Bear/Crash)
    # ═══════════════════════════════════════════════════════
    
    def _crisis_alpha(self, prices, volumes, price, atr, regime, regime_conf, cur_pos):
        """
        Capital preservation strategy for bear markets.
        Key principles:
        - Default: STAY IN CASH (best trade is no trade)
        - Only buy extreme oversold bounces (dead cat bounce trades)
        - VERY small positions, VERY tight stops
        - Goal: lose less than B&H (alpha from NOT losing)
        """
        factors = {}
        
        # 1. RSI extreme — only buy < 20
        rsi = _rsi(prices, 14)
        if rsi is not None:
            if rsi < 15: factors["rsi_extreme"] = 1.0
            elif rsi < 20: factors["rsi_extreme"] = 0.7
            elif rsi < 25: factors["rsi_extreme"] = 0.3
            else: factors["rsi_extreme"] = -0.5  # Not oversold enough
        else:
            factors["rsi_extreme"] = -0.5
        
        # 2. Capitulation volume spike (high volume + sharp drop = possible bottom)
        factors["volume_spike"] = 0
        if volumes and len(volumes) >= 20:
            avg_vol = sum(volumes[-20:]) / 20
            if avg_vol > 0 and len(prices) >= 2:
                vol_ratio = volumes[-1] / avg_vol
                price_drop = (prices[-1] / prices[-2] - 1)
                if vol_ratio > 2.0 and price_drop < -0.03:
                    factors["volume_spike"] = 0.6  # Capitulation signal
        
        # 3. Distance from recent high (how much has it already fallen?)
        if len(prices) >= 50:
            high_50 = max(prices[-50:])
            drawdown = (price / high_50) - 1
            if drawdown < -0.30:
                factors["deep_drawdown"] = 0.5  # Already down 30%+, bounce likely
            elif drawdown < -0.20:
                factors["deep_drawdown"] = 0.3
            else:
                factors["deep_drawdown"] = -0.3  # Not oversold enough
        else:
            factors["deep_drawdown"] = 0
        
        # 4. Short-term momentum reversal (3-day up after 10-day down)
        if len(prices) >= 13:
            ret_10 = prices[-4] / prices[-13] - 1  # Previous 10 bars
            ret_3 = prices[-1] / prices[-4] - 1     # Recent 3 bars
            if ret_10 < -0.08 and ret_3 > 0.02:
                factors["reversal"] = 0.6
            else:
                factors["reversal"] = -0.3
        else:
            factors["reversal"] = 0
        
        score = (
            factors["rsi_extreme"] * 0.35 +
            factors["volume_spike"] * 0.20 +
            factors["deep_drawdown"] * 0.25 +
            factors["reversal"] * 0.20
        )
        
        # VERY high threshold — almost never trade in bear
        if regime == MarketRegime.CRASH:
            threshold = 0.50  # Require extreme signal
        elif regime == MarketRegime.STRONG_BEAR:
            threshold = 0.40
        else:
            threshold = 0.30
        
        if score > threshold:
            signal = "buy"  # Never "strong_buy" in bear — always cautious
        elif score < -0.20:
            signal = "sell"
        else:
            signal = "hold"
        
        confidence = min(0.35 + abs(score) * 1.0, 0.80)  # Cap confidence low
        
        # Position sizing: TINY (capital preservation)
        pos_size = _clamp(self.risk_per_trade * 0.5, 0.03, 0.15)
        
        # Stops: TIGHT (cut losses fast in bear)
        stop_loss = price - atr * 1.2
        stop_loss = max(stop_loss, price * 0.95)  # Max 5% loss
        take_profit = price + atr * 2.0  # Quick profit target
        trailing_pct = atr * 1.2 / price
        
        reasoning = (f"CRISIS_ALPHA regime={regime.value} score={score:+.3f} "
                    f"rsi={factors['rsi_extreme']:+.2f} dd={factors.get('deep_drawdown',0):+.2f}")
        
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                          take_profit, trailing_pct, factors, reasoning)
    
    def _apply_regime_inertia(self, new_regime: MarketRegime, new_conf: float) -> MarketRegime:
        """
        Regime inertia: don't flip-flop between regimes.
        Stay in current regime unless new one has been consistent for N bars.
        This prevents false regime switches during pullbacks in bull markets.
        """
        if self._prev_regime is None:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime
        
        if new_regime == self._prev_regime:
            self._regime_hold_count = 0
            return new_regime
        
        # Regime changed — but is it real?
        self._regime_hold_count += 1
        
        # Allow fast transitions in/out of CRASH (urgent!)
        if new_regime == MarketRegime.CRASH:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime
        
        # Bull → non-Bull: require 5 bars to confirm (pullbacks are normal!)
        if self._prev_regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            required_bars = 5
        # Bear → non-Bear: require 3 bars
        elif self._prev_regime in (MarketRegime.STRONG_BEAR, MarketRegime.BEAR):
            required_bars = 3
        else:
            required_bars = 2
        
        if self._regime_hold_count >= required_bars:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime
        
        # Not enough evidence — stay in previous regime
        return self._prev_regime
    
    # ═══════════════════════════════════════════════════════
    # SHARED FACTORS
    # ═══════════════════════════════════════════════════════
    
    def _donchian_signal(self, prices: list[float]) -> float:
        period = self.donchian_period
        if len(prices) < period + 1:
            return 0.0
        channel = prices[-(period+1):-1]
        high = max(channel); low = min(channel)
        price = prices[-1]; mid = (high + low) / 2
        
        if price > high:
            strength = (price - high) / max(high - mid, 0.001)
            return _clamp(0.5 + strength * 0.5, 0, 1.0)
        elif price < low:
            strength = (low - price) / max(mid - low, 0.001)
            return _clamp(-0.5 - strength * 0.5, -1.0, 0)
        else:
            rng = max(high - low, 0.001)
            pos = (price - low) / rng
            return (pos - 0.5) * 0.3
    
    def _macd_momentum(self, prices: list[float]) -> float:
        if len(prices) < 26: return 0.0
        ema12 = _ema_val(prices, 12)
        ema26 = _ema_val(prices, 26)
        macd = ema12 - ema26
        if prices[-1] > 0:
            return _clamp(macd / prices[-1] * 100 * 3, -1, 1)
        return 0.0
    
    def _volume_confirm(self, prices, volumes) -> float:
        if not volumes or len(volumes) < 20 or not any(v > 0 for v in volumes[-20:]):
            return 0.0
        avg_vol = sum(volumes[-20:]) / 20
        if avg_vol == 0: return 0.0
        vol_ratio = volumes[-1] / avg_vol
        price_chg = (prices[-1] / prices[-2] - 1) if len(prices) >= 2 else 0
        if vol_ratio > 1.3 and price_chg > 0:
            return min(vol_ratio / 3, 1.0)
        elif vol_ratio > 1.3 and price_chg < 0:
            return -min(vol_ratio / 3, 1.0)
        return 0.0
    
    # ═══════════════════════════════════════════════════════
    # REGIME DETECTION v2 (improved)
    # ═══════════════════════════════════════════════════════
    
    def _detect_regime_v2(self, prices: list[float]) -> tuple[MarketRegime, float]:
        """
        Improved regime detection using multiple timeframes.
        Returns (regime, confidence).
        """
        n = len(prices)
        
        # Multi-timeframe returns
        ret_5 = (prices[-1] / prices[-5] - 1) if n >= 5 else 0
        ret_10 = (prices[-1] / prices[-10] - 1) if n >= 10 else 0
        ret_20 = (prices[-1] / prices[-20] - 1) if n >= 20 else 0
        ret_50 = (prices[-1] / prices[-50] - 1) if n >= 50 else 0
        
        # Volatility
        rets = [(prices[i]/prices[i-1]-1) for i in range(max(1, n-20), n)]
        vol = _stdev_s(rets) if len(rets) >= 2 else 0.02
        annualized_vol = vol * math.sqrt(252)
        
        # EMA alignment
        ema8 = _ema_val(prices, 8)
        ema21 = _ema_val(prices, 21)
        ema50 = _ema_val(prices, 50) if n >= 50 else ema21
        bull_aligned = ema8 > ema21 > ema50
        bear_aligned = ema8 < ema21 < ema50
        
        # ADX
        adx = _adx(prices, 14)
        
        # ── Decision tree ──
        
        # Crash: sharp recent drop
        if ret_5 < -0.07 and vol > 0.025:
            return MarketRegime.CRASH, 0.85
        
        # Strong Bear: sustained decline across timeframes
        if ret_20 < -0.10 and ret_50 < -0.15 and bear_aligned:
            return MarketRegime.STRONG_BEAR, 0.80
        
        # Bear: decline with ADX confirmation
        if ret_20 < -0.05 and ret_50 < -0.05 and bear_aligned:
            return MarketRegime.BEAR, 0.75
        
        # Strong Bull: all timeframes up, EMAs aligned, strong ADX
        if ret_20 > 0.08 and ret_50 > 0.15 and bull_aligned and adx > 25:
            return MarketRegime.STRONG_BULL, 0.85
        
        # Bull: rising with alignment
        if ret_20 > 0.03 and bull_aligned:
            return MarketRegime.BULL, 0.70
        
        # Also Bull if strong short-term and medium-term up
        if ret_10 > 0.05 and ret_20 > 0.02 and ema8 > ema21:
            return MarketRegime.BULL, 0.60
        
        # Volatile: high vol without clear direction
        if annualized_vol > 0.40:
            return MarketRegime.VOLATILE, 0.65
        
        # Ranging: everything else
        return MarketRegime.RANGING, 0.50
    
    # ═══════════════════════════════════════════════════════
    # TREND-SPECIFIC POSITION SIZING & STOPS
    # ═══════════════════════════════════════════════════════
    
    def _trend_position_size(self, price, atr, confidence, regime):
        """Large positions in trends — trend is our edge."""
        if atr <= 0 or price <= 0: return 0.1
        risk_pct = (atr * 2.5) / price  # Wide stop
        base = self.risk_per_trade / max(risk_pct, 0.005)
        size = base * confidence
        
        if regime == MarketRegime.STRONG_BULL:
            size *= 1.5  # Extra aggressive in strong trends
        elif regime == MarketRegime.VOLATILE:
            size *= 0.8  # Slightly smaller in volatile trends
        
        return _clamp(size, 0.10, self.max_position_size)
    
    def _trend_stops(self, prices, price, atr, regime):
        """Wide stops for trend-following — survive pullbacks."""
        lookback = min(20, len(prices) - 1)
        swing_low = min(prices[-lookback:]) if lookback > 0 else price * 0.90
        
        # Stop: below recent swing low with ATR buffer
        if regime == MarketRegime.STRONG_BULL:
            mult = 3.5  # Very wide
        elif regime == MarketRegime.VOLATILE:
            mult = 4.0  # Even wider in volatile (avoid whipsaw)
        else:
            mult = 3.0
        
        atr_stop = price - atr * mult
        swing_stop = swing_low - atr * 0.5
        stop_loss = max(atr_stop, swing_stop)
        stop_loss = max(stop_loss, price * 0.82)  # Never more than 18% below
        
        # NO take profit in trend — trailing stop only
        take_profit = price * 10.0  # Effectively infinite
        
        # Trailing: VERY wide in strong trends
        # Key insight: in a bull market, a 10-15% pullback is NORMAL
        # If our trailing is tighter than that, we get stopped out
        if regime == MarketRegime.STRONG_BULL:
            trailing_pct = max(atr * 4.5 / price, 0.16)  # Min 16% trailing
        elif regime == MarketRegime.VOLATILE:
            trailing_pct = max(atr * 5.0 / price, 0.18)  # Min 18% in volatile
        else:  # BULL
            trailing_pct = max(atr * 3.0 / price, 0.12)  # Min 12%
        
        return stop_loss, take_profit, trailing_pct


# ═══════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════

def _ema_val(prices: list[float], period: int) -> float:
    if len(prices) < period:
        return prices[-1] if prices else 0
    mult = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * mult + ema * (1 - mult)
    return ema

def _rsi(prices: list[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1: return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    recent = deltas[-period:]
    ag = sum(max(d, 0) for d in recent) / period
    al = sum(max(-d, 0) for d in recent) / period
    if al == 0: return 100.0
    return 100 - 100 / (1 + ag/al)

def _atr(prices: list[float], period: int = 14) -> float:
    if len(prices) < 2:
        return prices[-1] * 0.02 if prices else 0.02
    trs = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
    return sum(trs[-period:]) / min(len(trs), period)

def _adx(prices: list[float], period: int = 14) -> float:
    if len(prices) < period * 2: return 20.0
    plus_dm = []; minus_dm = []; tr_vals = []
    for i in range(1, len(prices)):
        hm = prices[i] - prices[i-1]; lm = prices[i-1] - prices[i]
        plus_dm.append(max(hm, 0) if hm > lm else 0)
        minus_dm.append(max(lm, 0) if lm > hm else 0)
        tr_vals.append(abs(prices[i] - prices[i-1]))
    def smooth(vals, n):
        if not vals: return [0]
        result = [sum(vals[:n]) / n]
        for v in vals[n:]:
            result.append(result[-1] * (n-1)/n + v/n)
        return result
    sp = smooth(plus_dm[-period*2:], period)
    sm = smooth(minus_dm[-period*2:], period)
    st = smooth(tr_vals[-period*2:], period)
    if not st or st[-1] == 0: return 20.0
    dp = 100 * sp[-1] / st[-1]; dm = 100 * sm[-1] / st[-1]
    diff = abs(dp - dm); total = dp + dm
    if total == 0: return 0.0
    return min(100 * diff / total * 1.3, 100)

def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2: return 0.0
    xm = (n-1)/2; ym = sum(values)/n
    num = sum((i-xm)*(v-ym) for i,v in enumerate(values))
    den = sum((i-xm)**2 for i in range(n))
    return num / max(den, 0.001)

def _stdev_s(values: list[float]) -> float:
    if len(values) < 2: return 0.0
    m = sum(values)/len(values)
    return math.sqrt(sum((v-m)**2 for v in values)/(len(values)-1))

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
