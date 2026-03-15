"""
WhaleTrader - Signal Engine v8: Hybrid Regime-Momentum Engine
==============================================================
Core insight from v7 experiments: we're strong in bear/correction but weak
in bull capture. v8 addresses this with:

1. BULL: More aggressive entry, wider initial trailing, no TP
2. VOLATILE: Split into vol-up/vol-down sub-modes with distinct strategies
3. RANGING: Smarter mean-reversion with faster TP cycle
4. BEAR: Bounce-trade with tighter risk
5. NEW: Volatility-scaled position sizing (higher vol → smaller pos but wider stops)
6. NEW: Momentum acceleration factor (2nd derivative of price)
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
    signal: str
    confidence: float
    regime: MarketRegime
    position_size: float
    stop_loss: float
    take_profit: float
    trailing_stop_pct: float
    factors: dict
    reasoning: str


class SignalEngineV8:
    def __init__(self):
        self._prev_regime = None
        self._regime_hold_count = 0
        self._consecutive_bull_bars = 0
        self._pending_buy_signal = 0
        self._bars_in_regime = 0

    def generate_signal(self, prices: list[float],
                        volumes: list[float] = None,
                        current_position: float = 0) -> SignalResult:
        n = len(prices)
        if n < 20:
            return SignalResult("hold", 0.3, MarketRegime.RANGING, 0, 0, 0, 0.05, {}, "warmup")

        price = prices[-1]
        atr = _atr(prices, min(14, n - 1))
        ann_vol = _rolling_vol(prices, 20)

        raw_regime, regime_conf = self._detect_regime(prices)
        regime = self._apply_inertia(raw_regime, regime_conf)

        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            self._consecutive_bull_bars += 1
        else:
            self._consecutive_bull_bars = 0

        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            return self._bull_signal(prices, volumes, price, atr, ann_vol, regime, current_position)
        elif regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH):
            return self._bear_signal(prices, volumes, price, atr, ann_vol, regime, current_position)
        elif regime == MarketRegime.VOLATILE:
            return self._volatile_signal(prices, volumes, price, atr, ann_vol, regime, current_position)
        else:
            return self._range_signal(prices, volumes, price, atr, ann_vol, regime, current_position)

    # ═══════════════════════════════════════════════════════
    # BULL SIGNAL
    # ═══════════════════════════════════════════════════════

    def _bull_signal(self, prices, volumes, price, atr, ann_vol, regime, cur_pos):
        factors = {}
        n = len(prices)

        mom_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        mom_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        mom_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        mom_50 = prices[-1] / prices[max(0, n - 51)] - 1 if n > 50 else mom_20

        vol_norm = max(ann_vol, 0.005)
        factors["momentum"] = _clamp(
            (mom_5 / vol_norm * 0.30 + mom_10 / vol_norm * 0.25 +
             mom_20 / vol_norm * 0.25 + mom_50 / vol_norm * 0.20) * 0.05, -1, 1)

        # Momentum acceleration (2nd derivative)
        if n > 10:
            mom_5_prev = prices[-6] / prices[max(0, n - 11)] - 1
            accel = mom_5 - mom_5_prev
            factors["acceleration"] = _clamp(accel * 20, -1, 1)
        else:
            factors["acceleration"] = 0

        ema5  = _ema_val(prices, min(5,  n))
        ema10 = _ema_val(prices, min(10, n))
        ema21 = _ema_val(prices, min(21, n))
        ema50 = _ema_val(prices, min(50, n))

        alignment = sum([price > ema5, ema5 > ema10, ema10 > ema21, ema21 > ema50])
        factors["ema_alignment"] = (alignment / 4.0) * 2 - 1

        ema_full_align = (ema5 > ema10 > ema21) and (price > ema5) and (mom_5 > 0)

        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None:
            if rsi > 80: factors["rsi"] = -0.3
            elif rsi > 60: factors["rsi"] = 0.3
            elif rsi < 35: factors["rsi"] = 0.8
            elif rsi < 45: factors["rsi"] = 0.5
            else: factors["rsi"] = 0.2
        else:
            factors["rsi"] = 0.2

        high_20 = max(prices[max(0, n-21):n-1]) if n > 2 else price
        factors["breakout"] = 0.7 if price > high_20 else -0.1

        if volumes and len(volumes) > 20:
            avg_vol = sum(volumes[-20:]) / 20
            factors["volume"] = _clamp((volumes[-1] / max(avg_vol, 1) - 1) * 2, -0.5, 0.8)
        else:
            factors["volume"] = 0.1

        score = (factors["momentum"]      * 0.25 +
                 factors["acceleration"]   * 0.10 +
                 factors["ema_alignment"]  * 0.25 +
                 factors["rsi"]            * 0.15 +
                 factors["breakout"]       * 0.15 +
                 factors["volume"]         * 0.10)

        if cur_pos == 0:
            if ema_full_align or factors["breakout"] > 0.5:
                signal = "strong_buy"
            elif score > -0.15:
                signal = "strong_buy" if score > 0.15 else "buy"
            else:
                signal = "hold"
        else:
            if score < -0.40:
                signal = "sell"
            elif score < -0.20 and not ema_full_align:
                signal = "sell"
            else:
                signal = "hold"

        confidence = min(0.60 + abs(score) * 0.7, 0.95)

        # Position sizing — match v7 (no vol adjustment)
        if regime == MarketRegime.STRONG_BULL:
            pos_size = 0.92
        elif regime == MarketRegime.BULL:
            pos_size = 0.80
        else:
            pos_size = 0.65

        if self._consecutive_bull_bars > 15:
            pos_size = min(pos_size * 1.10, 0.95)

        if regime == MarketRegime.STRONG_BULL:
            stop_pct = 0.28
        else:
            stop_pct = 0.22

        stop_loss    = price * (1 - stop_pct)
        take_profit  = price * 100.0
        trailing_pct = max(atr * 4.5 / price, stop_pct)

        self._pending_buy_signal = 0

        reasoning = (f"BULL score={score:+.3f} align={alignment}/4 "
                     f"accel={factors['acceleration']:+.2f} mom5={mom_5:+.2%}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # VOLATILE SIGNAL — split into vol-up/vol-down
    # ═══════════════════════════════════════════════════════

    def _volatile_signal(self, prices, volumes, price, atr, ann_vol, regime, cur_pos):
        n = len(prices)
        ret_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        ret_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        ema8 = _ema_val(prices, min(8, n))
        ema21 = _ema_val(prices, min(21, n))

        # Volatile-up: use bull strategy (no stop modification — let trend logic handle it)
        if (ret_10 > 0.02 and ret_5 > 0) or (price > ema8 > ema21 and ret_5 > 0):
            result = self._bull_signal(prices, volumes, price, atr, ann_vol, regime, cur_pos)
            result.position_size = min(result.position_size, 0.70)
            return result

        # Volatile-down: use bear strategy
        if ret_10 < -0.02 or ret_5 < -0.015:
            return self._bear_signal(prices, volumes, price, atr, ann_vol, regime, cur_pos)

        # Volatile-neutral: range strategy with smaller positions
        result = self._range_signal(prices, volumes, price, atr, ann_vol, regime, cur_pos)
        result.position_size = min(result.position_size * 0.8, 0.40)
        return result

    # ═══════════════════════════════════════════════════════
    # RANGE SIGNAL
    # ═══════════════════════════════════════════════════════

    def _range_signal(self, prices, volumes, price, atr, ann_vol, regime, cur_pos):
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

        mom_3 = prices[-1] / prices[max(0, n - 4)] - 1 if n > 3 else 0
        factors["short_mom"] = _clamp(mom_3 * 15, -1, 1)

        mom_1 = prices[-1] / prices[-2] - 1 if n > 1 else 0
        factors["reversal"] = 0.5 if (factors["z_score"] > 0.3 and mom_1 > 0) else 0

        score = (factors["z_score"]   * 0.35 +
                 factors["rsi"]       * 0.30 +
                 factors["short_mom"] * 0.20 +
                 factors["reversal"]  * 0.15)

        ret_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        if ret_20 < -0.08:
            buy_threshold = 0.40
        elif ret_20 < -0.04:
            buy_threshold = 0.25
        else:
            buy_threshold = 0.15

        raw_buy = score > buy_threshold
        raw_sell = score < -0.30

        if raw_buy:
            self._pending_buy_signal += 1
            if self._pending_buy_signal >= 2:
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
        pos_size = _clamp(0.45 * confidence, 0.20, 0.50)

        stop_loss   = max(price - atr * 2.0, price * 0.93)
        risk        = price - stop_loss
        take_profit = price + risk * 2.0
        trailing_pct = max(atr * 2.5 / price, 0.10)

        reasoning = (f"RANGE score={score:+.3f} z={factors['z_score']:+.2f} "
                     f"rsi={factors['rsi']:+.2f} pending={self._pending_buy_signal}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # BEAR SIGNAL
    # ═══════════════════════════════════════════════════════

    def _bear_signal(self, prices, volumes, price, atr, ann_vol, regime, cur_pos):
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
            factors["bounce"] = 0.7 if (ret_10 < -0.08 and ret_3 > 0.02) else (
                0.3 if (ret_10 < -0.06 and ret_3 > 0.01) else -0.3)
        else:
            factors["bounce"] = 0

        if volumes and len(volumes) > 20:
            avg_vol = sum(volumes[-20:]) / 20
            factors["capitulation"] = 0.5 if volumes[-1] > avg_vol * 2.0 else 0
        else:
            factors["capitulation"] = 0

        score = (factors["extreme_oversold"] * 0.45 +
                 factors["bounce"]           * 0.35 +
                 factors["capitulation"]     * 0.20)

        threshold = 0.45 if regime == MarketRegime.CRASH else 0.30

        if score > threshold:
            signal = "buy"
        elif cur_pos > 0:
            signal = "sell" if score < -0.20 else "hold"
        else:
            signal = "hold"

        confidence   = min(0.35 + abs(score) * 0.8, 0.75)
        pos_size     = _clamp(0.10, 0.05, 0.15)
        stop_loss    = price * 0.95
        take_profit  = price + atr * 2.5
        trailing_pct = max(atr * 1.5 / price, 0.06)

        self._pending_buy_signal = 0

        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, f"BEAR score={score:+.3f}")

    # ═══════════════════════════════════════════════════════
    # REGIME DETECTION
    # ═══════════════════════════════════════════════════════

    def _detect_regime(self, prices: list[float]) -> tuple[MarketRegime, float]:
        n = len(prices)

        ret_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        ret_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        ret_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0

        ema8  = _ema_val(prices, min(8,  n))
        ema21 = _ema_val(prices, min(21, n))
        p     = prices[-1]

        rets    = [prices[i] / prices[i - 1] - 1 for i in range(max(1, n - 20), n)]
        vol     = _stdev_s(rets) if len(rets) >= 2 else 0.02
        ann_vol = vol * math.sqrt(252)

        vol_scale = max(ann_vol / 0.30, 0.5)

        if ret_5 < -0.07 and vol > 0.025:
            return MarketRegime.CRASH, 0.85

        if ret_20 < -0.10 * vol_scale and ema8 < ema21:
            return MarketRegime.STRONG_BEAR, 0.80
        if ret_20 < -0.05 * vol_scale and ema8 < ema21:
            return MarketRegime.BEAR, 0.70

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

        if new_regime == MarketRegime.CRASH:
            self._prev_regime = new_regime
            self._regime_hold_count = 0
            return new_regime

        if new_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
            required = 2
        elif self._prev_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
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
