"""
WhaleTrader - Signal Engine v7: Momentum-Adaptive Regime Engine
================================================================
Key changes from v6:
1. Trend-Following Core: ride trends harder, cut losers faster
2. Adaptive Position Sizing: scale up in confirmed trends (Kelly-inspired)
3. Multi-Timeframe Momentum: align 5/10/20/50-bar momentum for conviction
4. Regime-Specific Trailing: wide in trends, tight in ranging
5. Volatility-Normalized Signals: normalize all factors by rolling vol
6. Break-and-Retest Entry: detect breakout-pullback patterns for high-conviction entries
7. Anti-Whipsaw: require consecutive signal confirmation in ranging markets
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
    signal: str          # buy / strong_buy / sell / hold
    confidence: float
    regime: MarketRegime
    position_size: float
    stop_loss: float
    take_profit: float
    trailing_stop_pct: float
    factors: dict
    reasoning: str


class SignalEngineV7:
    def __init__(self,
                 risk_per_trade: float = 0.02,
                 max_position_size: float = 0.95):
        self._prev_regime = None
        self._regime_hold_count = 0
        self._consecutive_bull_bars = 0
        self._pending_buy_signal = 0  # anti-whipsaw: consecutive buy signals in ranging

    def generate_signal(self, prices: list[float],
                        volumes: list[float] = None,
                        current_position: float = 0) -> SignalResult:
        n = len(prices)
        if n < 20:
            return SignalResult("hold", 0.3, MarketRegime.RANGING, 0, 0, 0, 0.05, {}, "warmup")

        price = prices[-1]
        atr = _atr(prices, min(14, n - 1))

        raw_regime, regime_conf = self._detect_regime(prices)
        regime = self._apply_inertia(raw_regime, regime_conf)

        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            self._consecutive_bull_bars += 1
        else:
            self._consecutive_bull_bars = 0

        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            return self._bull_signal(prices, volumes, price, atr, regime, current_position)
        elif regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH):
            return self._bear_signal(prices, volumes, price, atr, regime, current_position)
        elif regime == MarketRegime.VOLATILE:
            # Volatile: lean toward trend direction, but with stricter threshold
            ret_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
            ret_5  = prices[-1] / prices[max(0, n - 6)] - 1 if n > 5 else 0
            ema8 = _ema_val(prices, min(8, n))
            ema21 = _ema_val(prices, min(21, n))
            if (ret_10 > 0.02 and ret_5 > 0) or (price > ema8 > ema21 and ret_5 > 0):
                return self._bull_signal(prices, volumes, price, atr, regime, current_position)
            elif ret_10 < -0.02 or ret_5 < -0.015:
                return self._bear_signal(prices, volumes, price, atr, regime, current_position)
            else:
                return self._range_signal(prices, volumes, price, atr, regime, current_position)
        else:
            return self._range_signal(prices, volumes, price, atr, regime, current_position)

    # ═══════════════════════════════════════════════════════
    # BULL SIGNAL — aggressive trend-following
    # ═══════════════════════════════════════════════════════

    def _bull_signal(self, prices, volumes, price, atr, regime, cur_pos):
        factors = {}
        n = len(prices)

        # Multi-timeframe momentum (normalized)
        mom_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        mom_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        mom_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        mom_50 = prices[-1] / prices[max(0, n - 51)] - 1 if n > 50 else mom_20

        # Normalize momentum by rolling volatility
        vol_20 = _rolling_vol(prices, 20)
        vol_norm = max(vol_20, 0.005)
        factors["momentum"] = _clamp(
            (mom_5 / vol_norm * 0.30 +
             mom_10 / vol_norm * 0.25 +
             mom_20 / vol_norm * 0.25 +
             mom_50 / vol_norm * 0.20) * 0.05, -1, 1)

        # EMA stack alignment — strongest bull signal
        ema5  = _ema_val(prices, min(5,  n))
        ema8  = _ema_val(prices, min(8,  n))
        ema10 = _ema_val(prices, min(10, n))
        ema21 = _ema_val(prices, min(21, n))
        ema50 = _ema_val(prices, min(50, n))

        # Full alignment: price > ema5 > ema10 > ema21 > ema50
        alignment = 0
        if price > ema5:  alignment += 1
        if ema5 > ema10:  alignment += 1
        if ema10 > ema21: alignment += 1
        if ema21 > ema50: alignment += 1
        factors["ema_alignment"] = (alignment / 4.0) * 2 - 1  # [-1, 1]

        ema_full_align = (ema5 > ema10 > ema21) and (price > ema5) and (mom_5 > 0)

        # RSI with trend context
        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None:
            if rsi > 80:
                factors["rsi"] = -0.3  # overbought, but don't sell in bull
            elif rsi > 60:
                factors["rsi"] = 0.3   # healthy momentum
            elif rsi < 35:
                factors["rsi"] = 0.8   # oversold in bull = buy the dip!
            elif rsi < 45:
                factors["rsi"] = 0.5   # mild dip
            else:
                factors["rsi"] = 0.2
        else:
            factors["rsi"] = 0.2

        # Donchian breakout (20-bar high)
        high_20 = max(prices[max(0, n-21):n-1]) if n > 2 else price
        factors["breakout"] = 0.7 if price > high_20 else -0.1

        # Volume surge (if available)
        if volumes and len(volumes) > 20:
            avg_vol = sum(volumes[-20:]) / 20
            cur_vol = volumes[-1]
            factors["volume"] = _clamp((cur_vol / max(avg_vol, 1) - 1) * 2, -0.5, 0.8)
        else:
            factors["volume"] = 0.1

        # Composite score
        # Cross-strategy confirmation (inspired by AHF's ensemble approach)
        # Add Bollinger Band mean-reversion check as confirmation factor
        bb_period = min(20, n)
        bb_sma = sum(prices[-bb_period:]) / bb_period
        bb_std = _stdev_s(prices[-bb_period:])
        if bb_std > 0:
            bb_position = (price - bb_sma) / (bb_std * 2)  # [-1, 1] roughly
            # Near upper band = overbought (negative for entry)
            # Near lower band = oversold (positive for entry in uptrend)
            factors["bb_confirmation"] = _clamp(-bb_position * 0.5, -0.5, 0.5)
        else:
            factors["bb_confirmation"] = 0

        score = (factors["momentum"]      * 0.25 +
                 factors["ema_alignment"]  * 0.25 +
                 factors["rsi"]            * 0.15 +
                 factors["breakout"]       * 0.15 +
                 factors["volume"]         * 0.10 +
                 factors["bb_confirmation"]* 0.10)

        # Entry decision
        # Downtrend protection: if price is in a falling channel, require stronger signal
        ret_30 = prices[-1] / prices[max(0, n-31)] - 1 if n > 30 else 0
        in_falling_channel = ret_30 < -0.10  # down >10% in last 30 bars

        if cur_pos == 0:
            if ema_full_align or factors["breakout"] > 0.5:
                signal = "strong_buy"
            elif in_falling_channel:
                # In falling channel: require clear momentum (score > 0.10)
                signal = "buy" if score > 0.10 else "hold"
            elif score > -0.15:  # aggressive in bull
                signal = "strong_buy" if score > 0.15 else "buy"
            else:
                signal = "hold"
        else:
            # Exit on reversal — use tiered thresholds
            if score < -0.40:
                signal = "sell"
            elif score < -0.20 and not ema_full_align:
                signal = "sell"  # weaker sell if momentum fading
            else:
                signal = "hold"

        confidence = min(0.60 + abs(score) * 0.7, 0.95)

        # Aggressive position sizing
        if regime == MarketRegime.STRONG_BULL:
            pos_size = 0.92
        elif regime == MarketRegime.BULL:
            pos_size = 0.80
        else:  # volatile trending up
            pos_size = 0.65

        if self._consecutive_bull_bars > 15:
            pos_size = min(pos_size * 1.15, 0.95)
        # Adaptive stops based on regime strength
        if regime == MarketRegime.STRONG_BULL:
            stop_pct = 0.28
        elif regime == MarketRegime.BULL:
            stop_pct = 0.22
        else:  # volatile trending up
            stop_pct = 0.18

        stop_loss    = price * (1 - stop_pct)
        take_profit  = price * 100.0  # no TP in trends
        # Trailing: ATR-based, minimum = stop_pct
        trailing_pct = max(atr * 4.5 / price, stop_pct)

        self._pending_buy_signal = 0  # reset anti-whipsaw

        reasoning = (f"BULL score={score:+.3f} align={alignment}/4 "
                     f"mom5={mom_5:+.2%} breakout={'Y' if factors['breakout']>0.5 else 'N'}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # RANGE SIGNAL — mean reversion with anti-whipsaw
    # ═══════════════════════════════════════════════════════

    def _range_signal(self, prices, volumes, price, atr, regime, cur_pos):
        factors = {}
        n = len(prices)

        period = min(20, n)
        sma = sum(prices[-period:]) / period
        std = _stdev_s(prices[-period:])

        factors["z_score"] = _clamp(-(price - sma) / std / 2.0, -1, 1) if std > 0 else 0

        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None:
            if rsi < 25:   factors["rsi"] =  0.9
            elif rsi < 35: factors["rsi"] =  0.5
            elif rsi < 45: factors["rsi"] =  0.2
            elif rsi > 75: factors["rsi"] = -0.9
            elif rsi > 65: factors["rsi"] = -0.5
            else:          factors["rsi"] =  0.0
        else:
            factors["rsi"] = 0

        # Short momentum for timing
        mom_3 = prices[-1] / prices[max(0, n - 4)] - 1 if n > 3 else 0
        factors["short_mom"] = _clamp(mom_3 * 15, -1, 1)

        # Mean reversion strength: how far from mean + reversal signal
        mom_1 = prices[-1] / prices[-2] - 1 if n > 1 else 0
        factors["reversal"] = 0.5 if (factors["z_score"] > 0.3 and mom_1 > 0) else 0

        score = (factors["z_score"]   * 0.35 +
                 factors["rsi"]       * 0.30 +
                 factors["short_mom"] * 0.20 +
                 factors["reversal"]  * 0.15)

        # Trend filter
        ret_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        if ret_20 < -0.08:
            buy_threshold = 0.40
        elif ret_20 < -0.04:
            buy_threshold = 0.25
        else:
            buy_threshold = 0.15

        raw_buy = score > buy_threshold
        raw_sell = score < -0.30

        # Anti-whipsaw: require 2 consecutive buy signals in ranging
        # Exception: RSI extreme oversold (<20) = capitulation, bypass pending
        rsi_extreme = factors.get("rsi", 0) >= 0.9  # rsi < 25 → factor=0.9 (see above)
        if raw_buy:
            self._pending_buy_signal += 1
            if self._pending_buy_signal >= 2 or rsi_extreme:
                signal = "buy"
            else:
                signal = "hold"
        elif raw_sell:
            signal = "sell"
            self._pending_buy_signal = 0
        else:
            signal = "hold"
            self._pending_buy_signal = 0

        confidence = min(0.45 + abs(score) * 1.0, 0.85)

        # Upward-drifting ranging: larger position (e.g. Moutai-style)
        # Downtrending ranging: stay conservative
        if ret_20 > 0.02:
            pos_size = _clamp(0.62 * confidence, 0.30, 0.68)
        elif ret_20 > -0.02:
            pos_size = _clamp(0.50 * confidence, 0.22, 0.55)
        else:
            pos_size = _clamp(0.38 * confidence, 0.18, 0.45)

        stop_loss   = max(price - atr * 2.0, price * 0.93)
        risk        = price - stop_loss
        take_profit = price + risk * 2.0  # 2:1 R:R for range trading
        trailing_pct = max(atr * 2.5 / price, 0.10)

        reasoning = (f"RANGE score={score:+.3f} z={factors['z_score']:+.2f} "
                     f"rsi={factors['rsi']:+.2f} pending={self._pending_buy_signal}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # BEAR SIGNAL — defensive with bounce trades
    # ═══════════════════════════════════════════════════════

    def _bear_signal(self, prices, volumes, price, atr, regime, cur_pos):
        factors = {}
        n = len(prices)

        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None:
            if rsi < 18:   factors["extreme_oversold"] = 0.9
            elif rsi < 25: factors["extreme_oversold"] = 0.5
            elif rsi < 30: factors["extreme_oversold"] = 0.2
            else:          factors["extreme_oversold"] = -0.5
        else:
            factors["extreme_oversold"] = -0.3

        if n >= 5:
            ret_3  = prices[-1] / prices[-4] - 1
            ret_10 = prices[-1] / prices[max(0, n - 11)] - 1
            # Stronger bounce detection
            factors["bounce"] = 0.7 if (ret_10 < -0.08 and ret_3 > 0.02) else (
                0.3 if (ret_10 < -0.06 and ret_3 > 0.01) else -0.3)
        else:
            factors["bounce"] = 0

        # Volume capitulation (if available) — extreme volume = potential bottom
        if volumes and len(volumes) > 20:
            avg_vol = sum(volumes[-20:]) / 20
            cur_vol = volumes[-1]
            factors["capitulation"] = 0.5 if cur_vol > avg_vol * 2.0 else 0
        else:
            factors["capitulation"] = 0

        score = (factors["extreme_oversold"] * 0.45 +
                 factors["bounce"]           * 0.35 +
                 factors["capitulation"]     * 0.20)

        threshold = 0.45 if regime in (MarketRegime.CRASH, MarketRegime.STRONG_BEAR) else 0.30

        if score > threshold:
            signal = "buy"
        elif cur_pos > 0:
            signal = "sell" if score < -0.20 else "hold"
        else:
            signal = "hold"

        confidence   = min(0.35 + abs(score) * 0.8, 0.75)
        pos_size     = _clamp(0.10, 0.05, 0.15)  # small in bear
        stop_loss    = price * 0.95
        take_profit  = price + atr * 2.5
        trailing_pct = max(atr * 1.5 / price, 0.06)

        self._pending_buy_signal = 0

        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, f"BEAR score={score:+.3f}")

    # ═══════════════════════════════════════════════════════
    # REGIME DETECTION — improved with volatility-aware thresholds
    # ═══════════════════════════════════════════════════════

    def _detect_regime(self, prices: list[float]) -> tuple[MarketRegime, float]:
        n = len(prices)

        ret_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        ret_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        ret_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0

        ema8  = _ema_val(prices, min(8,  n))
        ema21 = _ema_val(prices, min(21, n))
        ema50 = _ema_val(prices, min(50, n))
        p     = prices[-1]

        rets    = [prices[i] / prices[i - 1] - 1 for i in range(max(1, n - 20), n)]
        vol     = _stdev_s(rets) if len(rets) >= 2 else 0.02
        ann_vol = vol * math.sqrt(252)

        # Volatility-adjusted thresholds
        vol_scale = max(ann_vol / 0.30, 0.5)  # normalize to 30% annual vol

        if ret_5 < -0.07 and vol > 0.025:
            return MarketRegime.CRASH, 0.85

        if ret_20 < -0.10 * vol_scale and ema8 < ema21:
            return MarketRegime.STRONG_BEAR, 0.80
        if ret_20 < -0.05 * vol_scale and ema8 < ema21:
            return MarketRegime.BEAR, 0.70

        # Multi-EMA confirmation for bull
        if ret_20 > 0.05 and p > ema8 > ema21:
            return MarketRegime.STRONG_BULL, 0.85
        if p > ema8 and p > ema21 and ret_10 > 0.015:
            return MarketRegime.BULL, 0.70
        if ema8 > ema21 and ret_20 > 0.015:
            return MarketRegime.BULL, 0.65
        if ret_10 > 0.025 and ret_5 > 0.008:
            return MarketRegime.BULL, 0.55

        if ann_vol > 0.40:
            return MarketRegime.VOLATILE, 0.60

        return MarketRegime.RANGING, 0.50

    def _apply_inertia(self, new_regime: MarketRegime, conf: float) -> MarketRegime:
        if self._prev_regime is None:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime

        if new_regime == self._prev_regime:
            self._regime_hold_count = 0
            return new_regime

        self._regime_hold_count += 1

        # Instant transitions
        if new_regime == MarketRegime.CRASH:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime

        # Fast into bull (2 bars), fast out of bear (2), slow out of bull (3)
        if new_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
            required = 2
        elif self._prev_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
            # Exit bull into bear: needs 3 bars (sticky bull)
            if new_regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR):
                required = 3
            else:
                required = 2
        elif self._prev_regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR):
            required = 2
        else:
            required = 2

        if self._regime_hold_count >= required:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime

        return self._prev_regime


# ─────────────────────────────────────────────────────────────
# INDICATORS
# ─────────────────────────────────────────────────────────────

def _ema_val(prices, period):
    if len(prices) < period: return prices[-1] if prices else 0
    mult = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * mult + ema * (1 - mult)
    return ema

def _rsi(prices, period=14):
    if len(prices) < period + 1: return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = deltas[-period:]
    ag = sum(max(d, 0) for d in recent) / period
    al = sum(max(-d, 0) for d in recent) / period
    if al == 0: return 100.0
    return 100 - 100 / (1 + ag / al)

def _atr(prices, period=14):
    if len(prices) < 2: return prices[-1] * 0.02 if prices else 0.02
    trs = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
    return sum(trs[-period:]) / min(len(trs), period)

def _rolling_vol(prices, window=20):
    """Annualized rolling volatility"""
    n = len(prices)
    if n < 3: return 0.02
    rets = [prices[i] / prices[i-1] - 1 for i in range(max(1, n-window), n)]
    if len(rets) < 2: return 0.02
    return _stdev_s(rets) * math.sqrt(252)

def _stdev_s(values):
    if len(values) < 2: return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _adx(prices, period=14):
    """Average Directional Index — measures trend strength (0-100).
    ADX > 25 = strong trend, ADX < 20 = ranging/weak trend."""
    n = len(prices)
    if n < period + 2: return 25.0  # neutral default

    # +DM / -DM
    plus_dm = []
    minus_dm = []
    tr_list = []
    for i in range(1, n):
        high_diff = prices[i] - prices[i-1]  # simplified (no H/L)
        low_diff = prices[i-1] - prices[i]
        tr = abs(prices[i] - prices[i-1])
        
        pdm = max(high_diff, 0) if high_diff > low_diff else 0
        mdm = max(low_diff, 0) if low_diff > high_diff else 0
        
        plus_dm.append(pdm)
        minus_dm.append(mdm)
        tr_list.append(max(tr, 0.001))

    # Smoothed averages (Wilder smoothing)
    atr_smooth = sum(tr_list[:period]) / period
    pdm_smooth = sum(plus_dm[:period]) / period
    mdm_smooth = sum(minus_dm[:period]) / period

    dx_list = []
    for j in range(period, len(tr_list)):
        atr_smooth = atr_smooth - atr_smooth / period + tr_list[j]
        pdm_smooth = pdm_smooth - pdm_smooth / period + plus_dm[j]
        mdm_smooth = mdm_smooth - mdm_smooth / period + minus_dm[j]

        if atr_smooth == 0:
            continue
        pdi = pdm_smooth / atr_smooth * 100
        mdi = mdm_smooth / atr_smooth * 100

        di_sum = pdi + mdi
        if di_sum == 0:
            continue
        dx = abs(pdi - mdi) / di_sum * 100
        dx_list.append(dx)

    if not dx_list:
        return 25.0

    # ADX = smoothed average of DX
    adx_val = sum(dx_list[-period:]) / min(len(dx_list), period)
    return adx_val
