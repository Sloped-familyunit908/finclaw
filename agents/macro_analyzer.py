"""
WhaleTrader — Macro Environment Analyzer
==========================================
Analyzes global macro factors that affect stock selection:

1. INTEREST RATES (Fed, PBOC, BOJ)
   - Rising rates → favor value, banks; hurt growth/tech
   - Falling rates → favor growth, tech, gold

2. CURRENCIES (DXY, USD/CNY, USD/JPY)
   - Strong USD → hurt emerging markets, commodities
   - Weak USD → favor gold, commodities, EM stocks

3. COMMODITIES (Oil, Gold, Copper)
   - Rising oil → favor energy, hurt consumer
   - Rising gold → risk-off signal, favor defensives
   - Rising copper → economic expansion signal

4. VOLATILITY (VIX)
   - High VIX (>25) → defensive, reduce exposure
   - Low VIX (<15) → risk-on, increase exposure

5. GEOPOLITICAL RISK FACTORS
   - US-China tension → favor domestic substitution (CN), defense (US)
   - War/conflict → favor energy, defense, gold
   - Trade barriers → favor domestic champions

Data sources: Yahoo Finance (^TNX, ^VIX, GC=F, CL=F, DX-Y.NYB, etc.)
"""
import math, sys, os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

try:
    import yfinance as yf
    import logging, warnings
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore")
except ImportError:
    yf = None


class MacroRegime(Enum):
    RISK_ON = "risk_on"           # Low VIX, rising stocks, falling gold
    RISK_OFF = "risk_off"         # High VIX, falling stocks, rising gold
    INFLATION = "inflation"       # Rising rates, rising commodities
    DEFLATION = "deflation"       # Falling rates, falling commodities
    TRANSITION = "transition"     # Mixed signals


@dataclass
class MacroSnapshot:
    regime: MacroRegime
    confidence: float
    vix: float
    us_10y_yield: float
    dxy_trend: str          # "strengthening" | "weakening" | "neutral"
    oil_trend: str
    gold_trend: str
    copper_trend: str
    sector_recommendations: dict   # sector -> weight adjustment
    reasoning: str


def _fetch_indicator(ticker, period="6mo"):
    """Fetch a macro indicator from Yahoo Finance."""
    if not yf: return None
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty: return None
        prices = [float(row["Close"]) for _, row in df.iterrows()]
        return prices
    except:
        return None


def _trend(prices, short=20, long=60):
    """Determine trend direction."""
    if not prices or len(prices) < short: return "neutral", 0
    recent = sum(prices[-short:]) / short
    if len(prices) >= long:
        older = sum(prices[-long:]) / long
    else:
        older = sum(prices) / len(prices)

    pct = (recent - older) / older if older != 0 else 0
    if pct > 0.03: return "rising", pct
    elif pct < -0.03: return "falling", pct
    return "neutral", pct


class MacroAnalyzer:
    """Analyzes global macro environment for stock selection."""

    # Sector sensitivity to macro factors
    SECTOR_MACRO_MAP = {
        # sector: {factor: sensitivity}
        "AI Infrastructure": {"rates": -0.3, "dxy": -0.2, "vix": -0.4, "gold": -0.1},
        "AI Software": {"rates": -0.4, "dxy": -0.1, "vix": -0.3, "gold": -0.1},
        "AI Platform": {"rates": -0.3, "dxy": -0.2, "vix": -0.3, "gold": -0.1},
        "Semiconductor": {"rates": -0.3, "dxy": -0.3, "vix": -0.4, "gold": -0.1},
        "China AI Infrastructure": {"rates": -0.2, "dxy": 0.3, "vix": -0.3, "gold": -0.1, "geopolitical": 0.4},
        "China Semiconductor": {"rates": -0.2, "dxy": 0.2, "vix": -0.2, "geopolitical": 0.5},
        "Clean Energy": {"rates": -0.4, "oil": -0.3, "vix": -0.2, "gold": -0.1},
        "EV / AI-Enhanced": {"rates": -0.3, "oil": -0.2, "vix": -0.2, "copper": 0.2},
        "Energy": {"rates": 0.1, "oil": 0.8, "vix": -0.1, "dxy": -0.2},
        "Resources": {"rates": 0.1, "copper": 0.6, "gold": 0.4, "dxy": -0.3},
        "Pharma Innovation": {"rates": -0.2, "vix": -0.1, "dxy": -0.1},
        "Defensive Consumer": {"rates": -0.1, "vix": 0.3, "gold": 0.1},
        "AI-Enhanced Retail": {"rates": -0.2, "vix": -0.1},
        "AI-Enhanced Finance": {"rates": 0.4, "vix": -0.3, "dxy": 0.1},
        "SaaS Disrupted": {"rates": -0.5, "vix": -0.3},
        "Legacy Tech": {"rates": -0.3, "vix": -0.3},
        "China Consumer": {"rates": -0.1, "dxy": 0.2, "vix": -0.1},
    }

    def get_macro_snapshot(self) -> MacroSnapshot:
        """Get current macro environment snapshot."""
        # Fetch indicators
        vix_prices = _fetch_indicator("^VIX", "3mo")
        tnx_prices = _fetch_indicator("^TNX", "6mo")       # US 10Y yield
        dxy_prices = _fetch_indicator("DX-Y.NYB", "6mo")   # Dollar index
        oil_prices = _fetch_indicator("CL=F", "6mo")       # WTI crude
        gold_prices = _fetch_indicator("GC=F", "6mo")      # Gold
        copper_prices = _fetch_indicator("HG=F", "6mo")    # Copper

        # Current values
        vix = vix_prices[-1] if vix_prices else 20.0
        us_10y = tnx_prices[-1] if tnx_prices else 4.0

        # Trends
        dxy_trend, dxy_chg = _trend(dxy_prices) if dxy_prices else ("neutral", 0)
        oil_trend, oil_chg = _trend(oil_prices) if oil_prices else ("neutral", 0)
        gold_trend, gold_chg = _trend(gold_prices) if gold_prices else ("neutral", 0)
        copper_trend, copper_chg = _trend(copper_prices) if copper_prices else ("neutral", 0)

        # Determine regime
        regime, confidence = self._determine_regime(
            vix, us_10y, dxy_trend, oil_trend, gold_trend, copper_trend,
            dxy_chg, oil_chg, gold_chg, copper_chg
        )

        # Sector recommendations
        sector_recs = self._compute_sector_weights(
            regime, vix, us_10y, dxy_trend, oil_trend, gold_trend, copper_trend
        )

        reasoning = (
            f"Regime={regime.value} | "
            f"VIX={vix:.1f} 10Y={us_10y:.2f}% | "
            f"DXY={dxy_trend}({dxy_chg:+.1%}) "
            f"Oil={oil_trend}({oil_chg:+.1%}) "
            f"Gold={gold_trend}({gold_chg:+.1%}) "
            f"Copper={copper_trend}({copper_chg:+.1%})"
        )

        return MacroSnapshot(
            regime=regime, confidence=confidence,
            vix=vix, us_10y_yield=us_10y,
            dxy_trend=dxy_trend, oil_trend=oil_trend,
            gold_trend=gold_trend, copper_trend=copper_trend,
            sector_recommendations=sector_recs,
            reasoning=reasoning,
        )

    def _determine_regime(self, vix, us_10y, dxy_t, oil_t, gold_t, copper_t,
                          dxy_c, oil_c, gold_c, copper_c):
        """Determine macro regime from indicators."""
        risk_on_signals = 0
        risk_off_signals = 0

        # VIX
        if vix < 15: risk_on_signals += 2
        elif vix < 20: risk_on_signals += 1
        elif vix > 25: risk_off_signals += 2
        elif vix > 20: risk_off_signals += 1

        # Gold (risk-off indicator)
        if gold_t == "rising": risk_off_signals += 1
        elif gold_t == "falling": risk_on_signals += 1

        # Copper (economic health)
        if copper_t == "rising": risk_on_signals += 1
        elif copper_t == "falling": risk_off_signals += 1

        # Rates
        inflation_signals = 0
        if us_10y > 4.5: inflation_signals += 1
        if oil_t == "rising": inflation_signals += 1
        if dxy_t == "strengthening": inflation_signals += 1

        if risk_on_signals > risk_off_signals + 1:
            return MacroRegime.RISK_ON, 0.7
        elif risk_off_signals > risk_on_signals + 1:
            return MacroRegime.RISK_OFF, 0.7
        elif inflation_signals >= 2:
            return MacroRegime.INFLATION, 0.6
        else:
            return MacroRegime.TRANSITION, 0.5

    def _compute_sector_weights(self, regime, vix, us_10y, dxy_t, oil_t, gold_t, copper_t):
        """Compute sector weight adjustments based on macro."""
        adjustments = {}

        for sector, sensitivities in self.SECTOR_MACRO_MAP.items():
            adj = 0

            # VIX impact
            if "vix" in sensitivities:
                if vix > 25:  # high fear
                    adj += sensitivities["vix"] * -0.5  # defensive sectors get boost
                elif vix < 15:  # low fear
                    adj += sensitivities["vix"] * 0.3

            # Rate impact
            if "rates" in sensitivities:
                if us_10y > 4.5:  # high rates
                    adj += sensitivities["rates"] * -0.3
                elif us_10y < 3.5:  # low rates
                    adj += sensitivities["rates"] * 0.3

            # DXY impact
            if "dxy" in sensitivities:
                if dxy_t == "rising":
                    adj += sensitivities["dxy"] * 0.2
                elif dxy_t == "falling":
                    adj += sensitivities["dxy"] * -0.2

            # Oil impact
            if "oil" in sensitivities:
                if oil_t == "rising":
                    adj += sensitivities["oil"] * 0.3
                elif oil_t == "falling":
                    adj += sensitivities["oil"] * -0.3

            # Gold impact
            if "gold" in sensitivities:
                if gold_t == "rising":
                    adj += sensitivities["gold"] * 0.3

            # Copper
            if "copper" in sensitivities:
                if copper_t == "rising":
                    adj += sensitivities["copper"] * 0.3

            # Geopolitical (always present for China)
            if "geopolitical" in sensitivities:
                adj += sensitivities["geopolitical"] * 0.1  # base geopolitical premium

            adjustments[sector] = round(adj, 3)

        return adjustments

    def adjust_stock_score(self, base_score: float, sector_theme: str) -> tuple[float, str]:
        """Adjust a stock's score based on current macro environment."""
        snapshot = self.get_macro_snapshot()
        sector_adj = snapshot.sector_recommendations.get(sector_theme, 0)
        adjusted = base_score + sector_adj

        reason = (
            f"Macro {snapshot.regime.value}: sector_adj={sector_adj:+.3f} | "
            f"VIX={snapshot.vix:.0f} Rates={snapshot.us_10y_yield:.1f}% "
            f"Oil={snapshot.oil_trend} Gold={snapshot.gold_trend}"
        )
        return adjusted, reason
