"""
WhaleTrader v9 — PARADIGM SHIFT: Stock Selection + Signal Engine
=================================================================
Key insight: Instead of optimizing signal timing on fixed scenarios,
add a PRE-FILTER layer that evaluates whether an asset is WORTH TRADING.

Human elite investor thinking:
1. Warren Buffett: "Be fearful when others are greedy" → contrarian filter
2. Stanley Druckenmiller: "Concentrated bets on high-conviction" → focus > diversification
3. Jesse Livermore: "The big money is in the sitting" → long holds in trends
4. George Soros: "Reflexivity" → momentum begets momentum
5. Jim Simons: "Statistical edge at scale" → quantify everything

NEW LAYERS:
Layer 0: ASSET SCORING — should we trade this at all?
Layer 1: REGIME DETECTION — market environment
Layer 2: SIGNAL GENERATION — when to enter/exit
Layer 3: POSITION MANAGEMENT — how much, trailing, pyramiding

The test bench should now include ASSET SELECTION capability:
given a basket of candidates, pick the best ones to allocate capital to.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AssetGrade(Enum):
    """Asset quality grade for stock selection"""
    A_PLUS = "A+"   # Strong trend, low risk → max allocation
    A = "A"          # Good trend → normal allocation
    B = "B"          # Tradeable but not ideal → reduced allocation
    C = "C"          # Poor setup → minimal or skip
    F = "F"          # Don't touch → avoid


@dataclass
class AssetScore:
    grade: AssetGrade
    momentum_score: float      # [-1, 1] trend strength
    quality_score: float       # [-1, 1] risk-adjusted quality
    timing_score: float        # [-1, 1] entry timing
    composite: float           # weighted final score
    allocation_pct: float      # suggested portfolio % (0-1)
    reasoning: str


class AssetSelector:
    """
    Pre-trade filter: evaluates if an asset is worth trading.
    
    Inspired by:
    - Dual Momentum (Gary Antonacci): absolute + relative momentum
    - Quality Factor (AQR): low vol, high Sharpe, stable growth
    - Mean reversion timing (DeMark): oversold bounces in quality assets
    """
    
    def score_asset(self, prices: list[float], volumes: list[float] = None,
                    benchmark_prices: list[float] = None) -> AssetScore:
        n = len(prices)
        if n < 60:
            return AssetScore(AssetGrade.C, 0, 0, 0, 0, 0.3, "insufficient data")
        
        # ═══ MOMENTUM SCORE ═══
        # Absolute momentum: is the asset trending up?
        ret_20 = prices[-1] / prices[-21] - 1
        ret_60 = prices[-1] / prices[-61] - 1
        ret_120 = prices[-1] / prices[max(0, n-121)] - 1 if n > 120 else ret_60
        
        # Hurst exponent proxy: are returns persistent or mean-reverting?
        # High autocorrelation → trending → better for momentum strategy
        rets = [prices[i]/prices[i-1]-1 for i in range(max(1,n-60), n)]
        autocorr = self._autocorrelation(rets, 1) if len(rets) > 5 else 0
        
        # Relative momentum (if benchmark provided)
        rel_mom = 0
        if benchmark_prices and len(benchmark_prices) >= 60:
            bench_ret = benchmark_prices[-1] / benchmark_prices[-61] - 1
            rel_mom = ret_60 - bench_ret
        
        ann_vol = _stdev_s(rets) * math.sqrt(252) if len(rets) > 1 else 0.30
        
        # Normalize momentum by volatility (risk-adjusted momentum)
        risk_adj_mom = ret_60 / max(ann_vol, 0.10) if ann_vol > 0 else 0
        
        momentum_score = _clamp(
            risk_adj_mom * 0.3 +          # risk-adjusted return
            (1 if ret_20 > 0 else -0.5) * 0.2 +  # recent direction
            autocorr * 0.2 +               # trend persistence
            _clamp(rel_mom * 3, -1, 1) * 0.15 +  # relative strength
            (1 if ret_120 > 0 else -0.3) * 0.15,  # long-term trend
            -1, 1
        )
        
        # ═══ QUALITY SCORE ═══
        # Volatility quality: lower vol → higher quality (Buffett-style)
        vol_quality = _clamp(1 - ann_vol / 0.50, -1, 1)
        
        # Drawdown quality: max drawdown in last 60 bars
        peak = prices[-60]
        max_dd = 0
        for p in prices[-60:]:
            peak = max(peak, p)
            dd = (p - peak) / peak
            max_dd = min(max_dd, dd)
        dd_quality = _clamp(1 + max_dd * 3, -1, 1)  # -33% DD → 0 quality
        
        # Trend consistency: % of days with positive returns
        pos_days = sum(1 for r in rets if r > 0) / max(len(rets), 1)
        consistency = _clamp((pos_days - 0.45) * 5, -1, 1)
        
        # Volume stability (if available)
        vol_stability = 0
        if volumes and len(volumes) > 20:
            recent_vols = volumes[-20:]
            avg_v = sum(recent_vols) / len(recent_vols)
            vol_cv = _stdev_s(recent_vols) / max(avg_v, 1)  # coefficient of variation
            vol_stability = _clamp(1 - vol_cv, -0.5, 0.5)
        
        quality_score = _clamp(
            vol_quality * 0.30 +
            dd_quality * 0.30 +
            consistency * 0.25 +
            vol_stability * 0.15,
            -1, 1
        )
        
        # ═══ TIMING SCORE ═══
        # RSI-based timing: oversold in uptrend = great entry
        rsi = _rsi(prices, 14)
        
        # Distance from moving averages
        ema21 = _ema_val(prices, 21)
        ema50 = _ema_val(prices, 50)
        dist_ema21 = (prices[-1] - ema21) / ema21
        dist_ema50 = (prices[-1] - ema50) / ema50
        
        # Best timing: price near support (ema) in uptrend
        if momentum_score > 0:
            # In uptrend: buy on pullback to EMA
            if rsi and rsi < 40:
                timing = 0.8  # oversold in uptrend = BUY
            elif rsi and rsi < 50:
                timing = 0.4
            elif dist_ema21 < 0.02:
                timing = 0.5  # near EMA support
            else:
                timing = 0.1  # uptrend but extended
        else:
            # In downtrend: timing is bad unless extreme oversold
            if rsi and rsi < 25:
                timing = 0.3  # bounce trade possible
            else:
                timing = -0.5  # don't try to catch falling knife
        
        timing_score = _clamp(timing, -1, 1)
        
        # ═══ COMPOSITE ═══
        composite = (
            momentum_score * 0.45 +   # trend is king
            quality_score  * 0.30 +   # quality compounds
            timing_score   * 0.25     # timing helps at the margin
        )
        
        # ═══ GRADE ═══
        if composite > 0.50:
            grade = AssetGrade.A_PLUS
            alloc = 0.90
        elif composite > 0.25:
            grade = AssetGrade.A
            alloc = 0.75
        elif composite > 0.05:
            grade = AssetGrade.B
            alloc = 0.55
        elif composite > -0.15:
            grade = AssetGrade.C
            alloc = 0.35
        else:
            grade = AssetGrade.F
            alloc = 0.0
        
        reasoning = (f"mom={momentum_score:+.2f} qual={quality_score:+.2f} "
                     f"timing={timing_score:+.2f} ret60={ret_60:+.1%} "
                     f"vol={ann_vol:.0%} dd={max_dd:.0%}")
        
        return AssetScore(grade, momentum_score, quality_score,
                          timing_score, composite, alloc, reasoning)
    
    def rank_assets(self, assets: dict[str, list[float]],
                    volumes: dict[str, list[float]] = None,
                    benchmark: list[float] = None,
                    top_n: int = 5) -> list[tuple[str, AssetScore]]:
        """Rank assets and return top N for trading."""
        scored = []
        for name, prices in assets.items():
            vols = volumes.get(name) if volumes else None
            score = self.score_asset(prices, vols, benchmark)
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1].composite, reverse=True)
        return scored[:top_n]
    
    def _autocorrelation(self, values, lag=1):
        if len(values) < lag + 2: return 0
        n = len(values)
        m = sum(values) / n
        c0 = sum((v-m)**2 for v in values) / n
        if c0 == 0: return 0
        ck = sum((values[i]-m)*(values[i-lag]-m) for i in range(lag, n)) / n
        return ck / c0


# ═══════════════════════════════════════════════════════════
# Import v7 signal engine as the core trading engine
# ═══════════════════════════════════════════════════════════
from agents.signal_engine_v7 import (
    SignalEngineV7, SignalResult, MarketRegime,
    _ema_val, _rsi, _atr, _rolling_vol, _stdev_s, _clamp
)


class SignalEngineV9(SignalEngineV7):
    """
    v9 = v7 core signal engine + Asset Selection layer.
    
    The signal generation is identical to v7.
    The difference is the OUTER LOOP that decides:
    1. Which assets to trade (AssetSelector)
    2. How much capital to allocate per asset
    3. Whether to skip an asset entirely
    """
    
    def __init__(self):
        super().__init__()
        self.asset_selector = AssetSelector()
    
    def evaluate_asset(self, prices, volumes=None, benchmark=None):
        """Pre-trade evaluation: should we trade this asset?"""
        return self.asset_selector.score_asset(prices, volumes, benchmark)
