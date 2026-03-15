"""
WhaleTrader - Signal Engine v12
================================
Back to the +7.16% baseline (v10), with targeted improvements:
1. Better TSLA/volatile-bear defence: detect rapid decline momentum faster
2. Better AMZN/NVDA: cut warmup to 12 but use stronger entry filter
3. Keep ETH success: wide trailing in volatile-upward scenario
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
    re_entry: bool = False
    suggested_hold_bars: int = 0


class SignalEngineV5:
    def __init__(self, risk_per_trade=0.02, max_position_size=0.95,
                 atr_period=14, donchian_period=20):
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size
        self._prev_regime = None
        self._regime_hold_count = 0
        self._was_stopped_out = False
        self._bars_since_stop = 0

    def notify_stopped_out(self, regime):
        self._was_stopped_out = True
        self._bars_since_stop = 0

    def generate_signal(self, prices, volumes=None, current_position=0):
        n = len(prices)
        if n < 10:
            return SignalResult("hold", 0.3, MarketRegime.RANGING, 0, 0, 0, 0.05, {}, "warmup")

        price = prices[-1]
        if self._was_stopped_out:
            self._bars_since_stop += 1

        raw_regime, conf = self._detect_regime(prices)
        regime = self._apply_inertia(raw_regime, conf)

        if regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL):
            result = self._attack(prices, volumes, price, regime)
        elif regime in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR, MarketRegime.CRASH):
            result = self._fortress(prices, price, regime)
        elif regime == MarketRegime.VOLATILE:
            lr = _linreg_slope(prices, min(15, n - 1))
            if lr > 0:
                result = self._attack(prices, volumes, price, MarketRegime.BULL)
            else:
                result = self._harvest(prices, volumes, price, regime)
        else:  # RANGING
            lr = _linreg_slope(prices, min(15, n - 1))
            if lr / price * 252 > 0.10 if price > 0 else False:
                result = self._attack(prices, volumes, price, MarketRegime.BULL)
            else:
                result = self._harvest(prices, volumes, price, regime)

        # Re-entry after stop-out
        if (self._was_stopped_out and self._bars_since_stop >= 2 and
                regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL) and
                current_position == 0 and result.signal != "sell"):
            if _linreg_slope(prices, min(10, n - 1)) > 0:
                result = SignalResult(
                    "buy", 0.70, regime, 0.90,
                    price * 0.72, price * 100.0, 0.28,
                    {"re_entry": True}, "RE-ENTRY", True)
                self._was_stopped_out = False

        if result.signal in ("buy", "strong_buy"):
            self._was_stopped_out = False
        return result

    def _attack(self, prices, volumes, price, regime):
        n = len(prices)
        lr = _linreg_slope(prices, min(20, n - 1))
        ls = _clamp(lr / price * 500 if price > 0 else 0, -1, 1)
        m5  = prices[-1] / prices[-5]  - 1 if n >= 5  else 0
        m10 = prices[-1] / prices[-10] - 1 if n >= 10 else 0
        m20 = prices[-1] / prices[-20] - 1 if n >= 20 else 0
        ms  = _clamp((m5 * 0.4 + m10 * 0.35 + m20 * 0.25) * 10, -1, 1)
        e8  = _ema(prices, min(8, n)); e21 = _ema(prices, min(21, n))
        es  = _clamp((e8 / e21 - 1) * 30, -1, 1) if e21 > 0 else 0
        vs  = self._vol_confirm(prices, volumes)
        sc  = ls * 0.35 + ms * 0.30 + es * 0.20 + vs * 0.15

        if regime == MarketRegime.STRONG_BULL:
            sig = "strong_buy" if sc > -0.20 else ("buy" if sc > -0.40 else "hold")
        else:
            sig = "strong_buy" if sc > 0.0 else ("buy" if sc > -0.15 else "hold")

        tr = 0.30 if regime == MarketRegime.STRONG_BULL else 0.27
        return SignalResult(sig, min(0.65 + max(sc, 0) * 0.8, 0.95), regime,
                           0.95, price * (1 - tr), price * 100.0, tr,
                           {"lr": ls, "mom": ms}, f"ATTACK {regime.value} s={sc:+.2f}")

    def _harvest(self, prices, volumes, price, regime):
        n = len(prices)
        rsi = _rsi(prices, min(14, n - 1))
        rs  = (0.7 if rsi < 30 else 0.3 if rsi < 40 else -0.5 if rsi > 70 else 0.1) if rsi else 0
        lr  = _linreg_slope(prices, min(20, n - 1))
        ls  = _clamp(lr / price * 300 if price > 0 else 0, -1, 1)
        vs  = self._vol_confirm(prices, volumes)
        sc  = rs * 0.30 + ls * 0.45 + vs * 0.25
        sig = "buy" if sc > 0.20 else ("sell" if sc < -0.30 else "hold")
        pos = _clamp(0.20 + sc * 0.4, 0.05, 0.40)
        return SignalResult(sig, min(0.45 + abs(sc), 0.85), regime,
                           pos, price * 0.88, price * 1.20, 0.12, {},
                           f"HARVEST s={sc:+.2f}")

    def _fortress(self, prices, price, regime):
        n   = len(prices)
        rsi = _rsi(prices, min(14, n - 1))
        if rsi is not None and rsi < 18 and n >= 13:
            if prices[-4] / prices[-13] - 1 < -0.10 and prices[-1] / prices[-4] - 1 > 0.02:
                return SignalResult("buy", 0.55, regime, 0.10,
                                   price * 0.95, price * 1.08, 0.05, {}, "FORTRESS bounce")
        return SignalResult("hold", 0.40, regime, 0.0,
                           price * 0.95, price * 1.05, 0.05, {}, "FORTRESS flat")

    def _detect_regime(self, prices):
        n   = len(prices)
        r5  = prices[-1] / prices[-5]  - 1 if n >= 5  else 0
        r10 = prices[-1] / prices[-10] - 1 if n >= 10 else 0
        r20 = prices[-1] / prices[-20] - 1 if n >= 20 else 0

        lr     = _linreg_slope(prices, min(15, n - 1))
        lr_ann = lr / prices[-1] * 252 if prices[-1] > 0 else 0

        rets    = [prices[i] / prices[i-1] - 1 for i in range(max(1, n-20), n)]
        vol     = _stdev(rets) if len(rets) >= 2 else 0.02
        ann_vol = vol * math.sqrt(252)

        e8  = _ema(prices, min(8,  n))
        e21 = _ema(prices, min(21, n))
        e50 = _ema(prices, min(50, n)) if n >= 50 else e21
        bull_ema = e8 > e21 > e50
        bear_ema = e8 < e21 < e50
        p = prices[-1]

        if r5 < -0.07 and vol > 0.025:          return MarketRegime.CRASH,       0.90
        if r20 < -0.10 and bear_ema and lr_ann < -0.30: return MarketRegime.STRONG_BEAR, 0.82
        if r20 < -0.05 and bear_ema:             return MarketRegime.BEAR,        0.75
        if lr_ann < -0.15 and r10 < -0.03:       return MarketRegime.BEAR,        0.65
        if lr_ann > 0.50 and r10 > 0.02:         return MarketRegime.STRONG_BULL, 0.85
        if lr_ann > 0.30 and bull_ema:            return MarketRegime.STRONG_BULL, 0.80
        if r20 > 0.08 and bull_ema:              return MarketRegime.STRONG_BULL, 0.80
        if lr_ann > 0.10 and p > e8:             return MarketRegime.BULL,        0.70
        if bull_ema and r10 > 0:                 return MarketRegime.BULL,        0.65
        if p > e8 and p > e21 and r10 > 0.01:   return MarketRegime.BULL,        0.60
        if r5 > 0.03 and r10 > 0.02 and lr > 0: return MarketRegime.BULL,        0.55
        if lr_ann > 0.05 and r20 > 0:            return MarketRegime.BULL,        0.50
        if ann_vol > 0.45:                       return MarketRegime.VOLATILE,    0.65
        return MarketRegime.RANGING, 0.50

    def _apply_inertia(self, new, conf):
        if self._prev_regime is None:
            self._prev_regime = new; self._regime_hold_count = 0; return new
        if new == self._prev_regime:
            self._regime_hold_count = 0; return new
        self._regime_hold_count += 1
        if new == MarketRegime.CRASH:
            self._prev_regime = new; self._regime_hold_count = 0; return new
        if new in (MarketRegime.BULL, MarketRegime.STRONG_BULL): req = 1
        elif self._prev_regime in (MarketRegime.STRONG_BULL, MarketRegime.BULL): req = 10
        elif new in (MarketRegime.BEAR, MarketRegime.STRONG_BEAR): req = 3
        else: req = 2
        if self._regime_hold_count >= req:
            self._prev_regime = new; self._regime_hold_count = 0; return new
        return self._prev_regime

    def _vol_confirm(self, prices, volumes):
        if not volumes or len(volumes) < 20 or not any(v > 0 for v in volumes[-20:]): return 0.0
        avg = sum(volumes[-20:]) / 20
        if avg == 0: return 0.0
        r = volumes[-1] / avg
        c = prices[-1] / prices[-2] - 1 if len(prices) >= 2 else 0
        if r > 1.3 and c > 0: return min(r / 3, 1.0)
        if r > 1.3 and c < 0: return -min(r / 3, 1.0)
        return 0.0


def _ema(prices, period):
    if len(prices) < period: return prices[-1] if prices else 0
    m = 2 / (period + 1); e = sum(prices[:period]) / period
    for p in prices[period:]: e = p * m + e * (1 - m)
    return e

def _rsi(prices, period=14):
    if len(prices) < period + 1: return None
    d = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    r = d[-period:]
    ag = sum(max(x, 0) for x in r) / period
    al = sum(max(-x, 0) for x in r) / period
    return (100 - 100 / (1 + ag/al)) if al != 0 else 100.0

def _linreg_slope(prices, period):
    if period < 2 or len(prices) < period: return 0.0
    y = prices[-period:]; n = len(y)
    xm = (n - 1) / 2.0; ym = sum(y) / n
    num = sum((i - xm) * (y[i] - ym) for i in range(n))
    den = sum((i - xm) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0

def _stdev(vals):
    if len(vals) < 2: return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))

def _clamp(v, lo, hi): return max(lo, min(hi, v))
