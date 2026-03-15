"""
WhaleTrader - Signal Engine v6: High-Participation Adaptive Engine
===================================================================
v6.5-stable — proven improvements only:
1. Ranging: lower buy threshold (0.15), bigger position (50%), short-mom factor
2. Bull: EMA-aligned instant entry (ema5>ema10>ema21 + price rising → buy)
3. Regime: fast into bull (1 bar), slow out (5 bars)
4. Everything else: original v6 behavior
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


class SignalEngineV6:
    def __init__(self,
                 risk_per_trade: float = 0.02,
                 max_position_size: float = 0.95):
        self._prev_regime = None
        self._regime_hold_count = 0
        self._consecutive_bull_bars = 0

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
            ret_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
            if ret_10 > 0.01:
                return self._bull_signal(prices, volumes, price, atr, regime, current_position)
            elif ret_10 < -0.02:
                return self._bear_signal(prices, volumes, price, atr, regime, current_position)
            else:
                return self._range_signal(prices, volumes, price, atr, regime, current_position)
        else:
            return self._range_signal(prices, volumes, price, atr, regime, current_position)

    # ═══════════════════════════════════════════════════════
    # BULL SIGNAL
    # ═══════════════════════════════════════════════════════

    def _bull_signal(self, prices, volumes, price, atr, regime, cur_pos):
        factors = {}
        n = len(prices)

        mom_5  = prices[-1] / prices[max(0, n - 6)]  - 1 if n > 5  else 0
        mom_10 = prices[-1] / prices[max(0, n - 11)] - 1 if n > 10 else 0
        mom_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        factors["momentum"] = _clamp(
            (mom_5 * 0.5 + mom_10 * 0.3 + mom_20 * 0.2) * 10, -1, 1)

        ema5  = _ema_val(prices, min(5,  n))
        ema8  = _ema_val(prices, min(8,  n))
        ema10 = _ema_val(prices, min(10, n))
        ema21 = _ema_val(prices, min(21, n))

        if ema21 > 0:
            factors["ema_position"] = _clamp((price - ema21) / ema21 * 10, -1, 1)
        else:
            factors["ema_position"] = 0

        # EMA alignment → fast entry
        ema_aligned = (ema5 > ema10 > ema21) and (price > ema5) and (mom_5 > 0)

        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None and rsi > 85:
            factors["rsi_warning"] = -0.5
        elif rsi is not None and rsi < 35:
            factors["rsi_warning"] = 0.8
        else:
            factors["rsi_warning"] = 0.2

        recent_vol = _stdev_s(
            [prices[i] / prices[i - 1] - 1 for i in range(max(1, n - 10), n)])
        avg_vol = _stdev_s(
            [prices[i] / prices[i - 1] - 1 for i in range(max(1, n - 30), n)]) if n > 30 else recent_vol
        factors["vol_squeeze"] = 0.5 if (avg_vol > 0 and recent_vol / avg_vol < 0.7) else 0

        score = (factors["momentum"]    * 0.35 +
                 factors["ema_position"] * 0.25 +
                 factors["rsi_warning"]  * 0.25 +
                 factors["vol_squeeze"]  * 0.15)

        if cur_pos == 0:
            if ema_aligned:
                signal = "strong_buy"
            elif score > -0.20:
                signal = "strong_buy" if score > 0.15 else "buy"
            else:
                signal = "hold"
        else:
            signal = "sell" if score < -0.40 else "hold"

        confidence = min(0.60 + abs(score) * 0.8, 0.95)

        if regime == MarketRegime.STRONG_BULL:
            pos_size = 0.90
        elif regime == MarketRegime.BULL:
            pos_size = 0.75
        else:
            pos_size = 0.60

        if self._consecutive_bull_bars > 10:
            pos_size = min(pos_size * 1.1, 0.95)

        if regime == MarketRegime.STRONG_BULL:
            stop_pct = 0.25
        else:
            stop_pct = 0.20

        stop_loss    = price * (1 - stop_pct)
        take_profit  = price * 100.0
        trailing_pct = max(atr * 4.0 / price, stop_pct)

        reasoning = (f"BULL score={score:+.3f} mom={factors['momentum']:+.2f} "
                     f"align={ema_aligned}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # RANGE SIGNAL  — improved thresholds & position size
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
            if rsi < 30:   factors["rsi"] =  0.8
            elif rsi < 40: factors["rsi"] =  0.4
            elif rsi > 70: factors["rsi"] = -0.8
            elif rsi > 60: factors["rsi"] = -0.4
            else:          factors["rsi"] =  0.0
        else:
            factors["rsi"] = 0

        mom_3 = prices[-1] / prices[max(0, n - 4)] - 1 if n > 3 else 0
        factors["short_mom"] = _clamp(mom_3 * 15, -1, 1)

        score = (factors["z_score"]   * 0.40 +
                 factors["rsi"]       * 0.35 +
                 factors["short_mom"] * 0.25)

        # Trend filter: don't buy in ranging if price trending down strongly
        ret_20 = prices[-1] / prices[max(0, n - 21)] - 1 if n > 20 else 0
        if ret_20 < -0.08:          # strong downtrend — be more cautious
            buy_threshold = 0.40    # much harder to enter
        elif ret_20 < -0.04:
            buy_threshold = 0.25
        else:
            buy_threshold = 0.15    # normal lower threshold

        # Lower buy threshold: 0.15 (was 0.30)
        if score > buy_threshold:
            signal = "buy"
        elif score < -0.30:
            signal = "sell"
        else:
            signal = "hold"

        confidence = min(0.45 + abs(score) * 1.0, 0.85)
        # Bigger position: 50% base (was 30%)
        pos_size = _clamp(0.50 * confidence, 0.20, 0.55)

        stop_loss   = max(price - atr * 1.8, price * 0.94)
        risk        = price - stop_loss
        take_profit = price + risk * 2.0
        trailing_pct = max(atr * 2.0 / price, 0.08)

        reasoning = (f"RANGE score={score:+.3f} z={factors['z_score']:+.2f} "
                     f"rsi={factors['rsi']:+.2f}")
        return SignalResult(signal, confidence, regime, pos_size, stop_loss,
                            take_profit, trailing_pct, factors, reasoning)

    # ═══════════════════════════════════════════════════════
    # BEAR SIGNAL
    # ═══════════════════════════════════════════════════════

    def _bear_signal(self, prices, volumes, price, atr, regime, cur_pos):
        factors = {}
        n = len(prices)

        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None and rsi < 20:
            factors["extreme_oversold"] = 0.8
        elif rsi is not None and rsi < 25:
            factors["extreme_oversold"] = 0.4
        else:
            factors["extreme_oversold"] = -0.5

        if n >= 5:
            ret_3  = prices[-1] / prices[-4] - 1
            ret_10 = prices[-1] / prices[max(0, n - 11)] - 1
            factors["bounce"] = 0.6 if (ret_10 < -0.08 and ret_3 > 0.02) else -0.3
        else:
            factors["bounce"] = 0

        score = factors["extreme_oversold"] * 0.55 + factors["bounce"] * 0.45
        threshold = 0.45 if regime == MarketRegime.CRASH else 0.35

        if score > threshold:
            signal = "buy"
        elif cur_pos > 0:
            signal = "sell" if score < -0.20 else "hold"
        else:
            signal = "hold"

        confidence   = min(0.35 + abs(score) * 0.8, 0.75)
        pos_size     = _clamp(0.10, 0.05, 0.15)
        stop_loss    = price * 0.95
        take_profit  = price + atr * 2.0
        trailing_pct = max(atr * 1.5 / price, 0.06)

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

        if ret_5 < -0.07 and vol > 0.025:
            return MarketRegime.CRASH, 0.85
        if ret_20 < -0.10 and ema8 < ema21:
            return MarketRegime.STRONG_BEAR, 0.80
        if ret_20 < -0.05 and ema8 < ema21:
            return MarketRegime.BEAR, 0.70
        if ret_20 > 0.06 and p > ema8 > ema21:
            return MarketRegime.STRONG_BULL, 0.85
        if p > ema8 and p > ema21 and ret_10 > 0.02:
            return MarketRegime.BULL, 0.70
        if ema8 > ema21 and ret_20 > 0.02:
            return MarketRegime.BULL, 0.65
        if ret_10 > 0.03 and ret_5 > 0.01:
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

        # Into bull: 2 bars confirmation; out of bull into bear: 3 bars; other: 2 bars
        if new_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
            required = 2  # was 1 — need confirmation before large bull position
        elif self._prev_regime in (MarketRegime.BULL, MarketRegime.STRONG_BULL):
            required = 3  # was 5 — exit bull faster to cut losses
        elif self._prev_regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR):
            required = 3
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

def _stdev_s(values):
    if len(values) < 2: return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))
