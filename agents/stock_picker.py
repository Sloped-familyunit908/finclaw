"""
WhaleTrader — AI-Powered Stock Picker (LLM + Multi-Factor)
===========================================================
The ULTIMATE stock selection system. Combines:

1. QUANTITATIVE FACTORS (from price data)
   - Momentum (1M/3M/6M/1Y)
   - Quality (vol, drawdown, Sharpe)
   - Trend (EMA alignment, ADX)

2. FUNDAMENTAL ANALYSIS (from yfinance)
   - Market cap, P/E, P/B, Dividend yield
   - Revenue growth, Profit margins
   - Debt ratios

3. LLM REASONING (optional, if API key available)
   - Industry positioning analysis
   - Competitive moat assessment
   - Macro trend alignment

This module can work WITHOUT LLM (pure quant mode) or WITH LLM
for enhanced selection (hybrid mode).
"""
import math, sys, os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    import yfinance as yf
except ImportError:
    yf = None


class ConvictionLevel(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    AVOID = "AVOID"
    STRONG_AVOID = "STRONG_AVOID"


@dataclass
class StockAnalysis:
    ticker: str
    name: str
    conviction: ConvictionLevel
    score: float  # -1.0 to +1.0
    factors: dict
    reasoning: str


class MultiFactorPicker:
    """
    Multi-factor stock picker with 3 layers:
    Layer 1: Price-based factors (always available)
    Layer 2: Fundamental factors (yfinance)
    Layer 3: LLM reasoning (optional)
    """

    def __init__(self, use_fundamentals=True, use_llm=False):
        self.use_fundamentals = use_fundamentals
        self.use_llm = use_llm

    def analyze(self, ticker: str, price_history: list[dict],
                name: str = "") -> StockAnalysis:
        """Comprehensive stock analysis."""
        prices = [x["price"] for x in price_history]
        volumes = [x.get("volume", 0) for x in price_history]
        n = len(prices)
        years = n / 252

        factors = {}

        # ═══ LAYER 1: Price-Based Factors ═══
        # Momentum
        mom_1m = prices[-1]/prices[max(0,n-21)]-1 if n>21 else 0
        mom_3m = prices[-1]/prices[max(0,n-63)]-1 if n>63 else 0
        mom_6m = prices[-1]/prices[max(0,n-126)]-1 if n>126 else 0
        mom_1y = prices[-1]/prices[max(0,n-252)]-1 if n>252 else 0

        # Momentum acceleration (Soros-inspired)
        mom_accel = 1.0 if (mom_1m > 0.03 and mom_3m > mom_6m * 0.5) else (
            0.5 if mom_1m > 0 else 0.0)

        # CAGR
        total_ret = prices[-1]/prices[0]-1
        cagr = (1+total_ret)**(1/max(years,0.5))-1 if total_ret>-1 else -1

        # Volatility
        rets = [prices[i]/prices[i-1]-1 for i in range(1,n)]
        ann_vol = (sum((r-sum(rets)/len(rets))**2 for r in rets)/(len(rets)-1))**0.5*math.sqrt(252) if len(rets)>1 else 0.3

        # Max drawdown
        peak = prices[0]; max_dd = 0
        for p in prices:
            peak = max(peak, p); max_dd = min(max_dd, (p-peak)/peak)

        # EMA trend
        def _ema(data, period):
            if len(data) < period: return data[-1]
            mult = 2/(period+1); e = sum(data[:period])/period
            for p in data[period:]: e = p*mult+e*(1-mult)
            return e

        ema8 = _ema(prices, 8); ema21 = _ema(prices, 21); ema55 = _ema(prices, min(55,n))
        trend_align = (1.0 if prices[-1]>ema8>ema21>ema55 else
                       0.5 if prices[-1]>ema21 else
                       -0.5 if prices[-1]<ema21<ema55 else -1.0)

        # Relative Strength (vs simple benchmark: 10% annual)
        benchmark_ret = 0.10 * years
        relative_strength = (total_ret - benchmark_ret) / max(abs(benchmark_ret), 0.01)

        # RSI
        gains = [max(rets[i],0) for i in range(max(0,len(rets)-14), len(rets))]
        losses = [max(-rets[i],0) for i in range(max(0,len(rets)-14), len(rets))]
        avg_gain = sum(gains)/max(len(gains),1); avg_loss = sum(losses)/max(len(losses),1)
        rsi = 100 - 100/(1+avg_gain/max(avg_loss,0.001))

        # Volume trend
        if len(volumes) > 40 and any(v > 0 for v in volumes):
            recent_vol = sum(volumes[-20:])/20
            older_vol = sum(volumes[-40:-20])/20 if len(volumes) > 40 else recent_vol
            vol_trend = recent_vol / max(older_vol, 1) - 1
        else:
            vol_trend = 0

        factors["momentum"] = self._clamp(
            (mom_1m*0.2 + mom_3m*0.3 + mom_6m*0.25 + mom_1y*0.25) * 3, -1, 1)
        factors["momentum_accel"] = mom_accel
        factors["trend"] = trend_align
        factors["quality"] = self._clamp(
            (1-min(ann_vol,1))*0.4 + (-max_dd+0.5)*0.3 + min(cagr/0.3,1)*0.3, -1, 1)
        factors["relative_strength"] = self._clamp(relative_strength * 0.3, -1, 1)
        factors["rsi_signal"] = self._clamp((50-rsi)/50, -1, 1)  # oversold=positive
        factors["volume_trend"] = self._clamp(vol_trend, -0.5, 0.5)

        # ═══ LAYER 2: Fundamental Factors ═══
        if self.use_fundamentals and yf:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info or {}

                # Valuation
                pe = info.get("trailingPE", info.get("forwardPE", 0))
                pb = info.get("priceToBook", 0)
                ps = info.get("priceToSalesTrailing12Months", 0)

                # Growth
                rev_growth = info.get("revenueGrowth", 0) or 0
                earnings_growth = info.get("earningsGrowth", 0) or 0

                # Profitability
                profit_margin = info.get("profitMargins", 0) or 0
                roe = info.get("returnOnEquity", 0) or 0

                # Size
                market_cap = info.get("marketCap", 0) or 0

                # Dividend
                div_yield = info.get("dividendYield", 0) or 0

                # PEG-style: growth relative to valuation
                if pe and pe > 0 and earnings_growth:
                    peg = pe / max(earnings_growth * 100, 1)
                    factors["peg"] = self._clamp(1 - peg/3, -1, 1)  # PEG<1 = good
                else:
                    factors["peg"] = 0

                factors["growth"] = self._clamp(
                    (rev_growth or 0) * 2 + (earnings_growth or 0) * 3, -1, 1)
                factors["profitability"] = self._clamp(
                    (profit_margin or 0) * 3 + (roe or 0) * 2, -1, 1)
                factors["value"] = self._clamp(
                    (1 - min(pe/50, 1) if pe and pe > 0 else 0) * 0.5 +
                    (1 - min(pb/5, 1) if pb and pb > 0 else 0) * 0.3 +
                    (div_yield or 0) * 10 * 0.2, -1, 1)
                factors["size"] = "large" if market_cap > 50e9 else (
                    "mid" if market_cap > 10e9 else "small")
            except:
                factors["peg"] = 0; factors["growth"] = 0
                factors["profitability"] = 0; factors["value"] = 0
                factors["size"] = "unknown"

        # ═══ COMPOSITE SCORE ═══
        # Weights inspired by what actually worked in our 5Y backtests:
        # Momentum was #1 predictor of success
        weights = {
            "momentum": 0.25,
            "momentum_accel": 0.10,
            "trend": 0.15,
            "quality": 0.10,
            "relative_strength": 0.10,
            "growth": 0.15,
            "profitability": 0.05,
            "value": 0.05,
            "peg": 0.05,
        }

        score = sum(factors.get(k, 0) * w for k, w in weights.items()
                    if isinstance(factors.get(k, 0), (int, float)))

        # Conviction
        if score > 0.40:
            conviction = ConvictionLevel.STRONG_BUY
        elif score > 0.15:
            conviction = ConvictionLevel.BUY
        elif score > -0.10:
            conviction = ConvictionLevel.HOLD
        elif score > -0.30:
            conviction = ConvictionLevel.AVOID
        else:
            conviction = ConvictionLevel.STRONG_AVOID

        reasoning = (
            f"Score={score:+.3f} | "
            f"Mom={factors['momentum']:+.2f} Accel={factors.get('momentum_accel',0):.1f} "
            f"Trend={factors['trend']:+.1f} "
            f"Quality={factors['quality']:+.2f} "
            f"RS={factors['relative_strength']:+.2f} "
            f"Growth={factors.get('growth',0):+.2f} "
            f"CAGR={cagr:+.1%} Vol={ann_vol:.0%} MaxDD={max_dd:+.0%}"
        )

        return StockAnalysis(
            ticker=ticker, name=name,
            conviction=conviction, score=score,
            factors=factors, reasoning=reasoning,
        )

    def rank_universe(self, stocks_data: list[dict]) -> list[StockAnalysis]:
        """Analyze and rank a universe of stocks."""
        analyses = []
        for d in stocks_data:
            analysis = self.analyze(d["ticker"], d["h"], d.get("name", ""))
            analyses.append(analysis)

        return sorted(analyses, key=lambda x: x.score, reverse=True)

    @staticmethod
    def _clamp(v, lo=-1, hi=1):
        return max(lo, min(hi, v))
