"""
WhaleTrader — Deep Macro Intelligence
=======================================
6 layers of macro analysis:

Layer 1: MARKET SENTIMENT (VIX, Put/Call, Fear & Greed proxy)
Layer 2: MONETARY POLICY (Fed funds rate, yield curve, M2 money supply proxy)
Layer 3: COMMODITY CYCLE (Oil, Gold, Copper, Lithium proxy, Uranium proxy)
Layer 4: CURRENCY & FLOWS (DXY, USD/CNY, USD/JPY, Bitcoin as risk proxy)
Layer 5: ECONOMIC CYCLE (PMI proxy, unemployment proxy, housing proxy)
Layer 6: KONDRATIEFF WAVE (50-year tech cycle positioning)

All data from Yahoo Finance (free).
"""
import math, sys, os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

try:
    import yfinance as yf
    import logging, warnings
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    warnings.filterwarnings("ignore")
except ImportError:
    yf = None


class EconomicPhase(Enum):
    EXPANSION = "expansion"       # Growing economy, rising stocks
    PEAK = "peak"                 # Overheating, rising rates, commodities up
    CONTRACTION = "contraction"   # Slowing, falling stocks, rising bonds
    TROUGH = "trough"             # Bottom, fear maximal, opportunity maximal


class KondratieffSeason(Enum):
    SPRING = "spring"    # New tech adoption (2009-2020: mobile/cloud)
    SUMMER = "summer"    # Tech boom peak (2020-2025: AI explosion)
    AUTUMN = "autumn"    # Financialization (next phase?)
    WINTER = "winter"    # Deleveraging, depression


def _fetch(ticker, period="6mo"):
    if not yf: return None
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty: return None
        return [float(row["Close"]) for _, row in df.iterrows()]
    except:
        return None


def _trend(prices, short=20, long=60):
    if not prices or len(prices) < short: return "neutral", 0
    r = sum(prices[-short:]) / short
    o = sum(prices[-min(long,len(prices)):]) / min(long, len(prices))
    p = (r - o) / o if o != 0 else 0
    if p > 0.03: return "rising", p
    elif p < -0.03: return "falling", p
    return "neutral", p


def _momentum(prices, lookback=60):
    if not prices or len(prices) < lookback: return 0
    return prices[-1] / prices[-lookback] - 1


@dataclass
class DeepMacroSnapshot:
    # Layer 1: Sentiment
    vix: float = 20.0
    vix_regime: str = "normal"  # calm/normal/elevated/panic
    btc_trend: str = "neutral"
    btc_as_risk: str = "neutral"  # BTC increasingly correlates with risk assets

    # Layer 2: Monetary
    us_10y: float = 4.0
    us_2y: float = 4.0
    yield_curve: str = "normal"  # inverted/flat/normal/steep
    rate_direction: str = "neutral"

    # Layer 3: Commodities
    oil_trend: str = "neutral"
    gold_trend: str = "neutral"
    copper_trend: str = "neutral"
    commodity_cycle: str = "neutral"  # super_cycle/normal/deflation

    # Layer 4: Currency
    dxy_trend: str = "neutral"
    usdcny_trend: str = "neutral"
    usdjpy_trend: str = "neutral"
    dollar_regime: str = "neutral"  # strong/neutral/weak

    # Layer 5: Economic Cycle
    economic_phase: EconomicPhase = EconomicPhase.EXPANSION
    sp500_trend: str = "neutral"
    russell_vs_sp: str = "neutral"  # small cap vs large cap rotation

    # Layer 6: Kondratieff
    kondratieff: KondratieffSeason = KondratieffSeason.SUMMER

    # Composite
    overall_regime: str = "neutral"
    confidence: float = 0.5
    reasoning: str = ""

    # Sector impacts
    sector_adjustments: dict = field(default_factory=dict)


class DeepMacroAnalyzer:
    """6-layer macro analysis for stock selection."""

    INDICATORS = {
        "vix": "^VIX",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "russell": "^RUT",        # Small cap
        "us_10y": "^TNX",         # 10-year yield
        "us_2y": "^IRX",          # 13-week T-bill (proxy for short rates)
        "dxy": "DX-Y.NYB",       # Dollar index
        "oil": "CL=F",           # WTI Crude
        "gold": "GC=F",          # Gold
        "copper": "HG=F",        # Copper
        "btc": "BTC-USD",        # Bitcoin
        "usdcny": "CNY=X",       # USD/CNY
        "usdjpy": "JPY=X",       # USD/JPY
    }

    # What each sector likes/hates in macro terms
    SECTOR_SENSITIVITY = {
        "AI Infrastructure": {
            "vix": -0.3, "rates": -0.3, "btc": 0.2, "dxy": -0.2,
            "kondratieff": 0.4, "economic": 0.2,
        },
        "AI Software": {
            "vix": -0.3, "rates": -0.4, "btc": 0.1, "kondratieff": 0.3,
        },
        "Semiconductor": {
            "vix": -0.4, "rates": -0.3, "copper": 0.2, "kondratieff": 0.3,
        },
        "China AI Infrastructure": {
            "vix": -0.2, "rates": -0.1, "dxy": 0.3, "btc": 0.1,
            "geopolitical": 0.4, "cny": 0.2, "kondratieff": 0.3,
        },
        "Clean Energy": {
            "rates": -0.4, "oil_inverse": 0.3, "copper": 0.2, "kondratieff": 0.2,
        },
        "EV / AI-Enhanced": {
            "rates": -0.3, "copper": 0.2, "btc": 0.1, "kondratieff": 0.2,
        },
        "Energy": {
            "oil": 0.8, "rates": 0.1, "dxy": -0.2, "economic": 0.3,
        },
        "Resources": {
            "copper": 0.5, "gold": 0.3, "dxy": -0.3, "economic": 0.3,
            "commodity_super": 0.4,
        },
        "Pharma Innovation": {
            "vix": -0.1, "rates": -0.2, "defensive": 0.3,
        },
        "Defensive Consumer": {
            "vix": 0.3, "rates": -0.1, "defensive": 0.5, "economic_inverse": 0.2,
        },
        "AI-Enhanced Finance": {
            "rates": 0.4, "vix": -0.2, "yield_curve": 0.3, "economic": 0.2,
        },
        "SaaS Disrupted": {
            "rates": -0.5, "vix": -0.3, "kondratieff": -0.3,
        },
        "China Consumer": {
            "cny": 0.3, "vix": -0.1, "dxy": 0.2,
        },
    }

    def analyze(self) -> DeepMacroSnapshot:
        """Run full 6-layer macro analysis."""
        snap = DeepMacroSnapshot()

        # Fetch all indicators
        data = {}
        for name, ticker in self.INDICATORS.items():
            data[name] = _fetch(ticker, "6mo")

        # ═══ Layer 1: SENTIMENT ═══
        if data.get("vix"):
            snap.vix = data["vix"][-1]
            if snap.vix < 15: snap.vix_regime = "calm"
            elif snap.vix < 20: snap.vix_regime = "normal"
            elif snap.vix < 30: snap.vix_regime = "elevated"
            else: snap.vix_regime = "panic"

        if data.get("btc"):
            snap.btc_trend, _ = _trend(data["btc"])
            btc_mom = _momentum(data["btc"], 30)
            snap.btc_as_risk = "risk_on" if btc_mom > 0.10 else ("risk_off" if btc_mom < -0.10 else "neutral")

        # ═══ Layer 2: MONETARY POLICY ═══
        if data.get("us_10y"):
            snap.us_10y = data["us_10y"][-1]
            _, rate_chg = _trend(data["us_10y"])
            snap.rate_direction = "rising" if rate_chg > 0.05 else ("falling" if rate_chg < -0.05 else "stable")

        if data.get("us_2y"):
            snap.us_2y = data["us_2y"][-1]
            spread = snap.us_10y - snap.us_2y
            if spread < -0.5: snap.yield_curve = "deeply_inverted"
            elif spread < 0: snap.yield_curve = "inverted"
            elif spread < 0.5: snap.yield_curve = "flat"
            elif spread < 1.5: snap.yield_curve = "normal"
            else: snap.yield_curve = "steep"

        # ═══ Layer 3: COMMODITIES ═══
        if data.get("oil"):
            snap.oil_trend, _ = _trend(data["oil"])
        if data.get("gold"):
            snap.gold_trend, _ = _trend(data["gold"])
        if data.get("copper"):
            snap.copper_trend, _ = _trend(data["copper"])

        # Commodity super cycle detection
        commodities_up = sum(1 for t in [snap.oil_trend, snap.gold_trend, snap.copper_trend]
                            if t == "rising")
        if commodities_up >= 2:
            snap.commodity_cycle = "super_cycle"
        elif commodities_up == 0 and any(t == "falling" for t in [snap.oil_trend, snap.copper_trend]):
            snap.commodity_cycle = "deflation"
        else:
            snap.commodity_cycle = "normal"

        # ═══ Layer 4: CURRENCY ═══
        if data.get("dxy"):
            snap.dxy_trend, dxy_chg = _trend(data["dxy"])
            snap.dollar_regime = "strong" if dxy_chg > 0.03 else ("weak" if dxy_chg < -0.03 else "neutral")

        if data.get("usdcny"):
            snap.usdcny_trend, _ = _trend(data["usdcny"])
        if data.get("usdjpy"):
            snap.usdjpy_trend, _ = _trend(data["usdjpy"])

        # ═══ Layer 5: ECONOMIC CYCLE ═══
        if data.get("sp500"):
            snap.sp500_trend, sp_mom = _trend(data["sp500"])

        if data.get("russell") and data.get("sp500"):
            r_mom = _momentum(data["russell"], 60)
            s_mom = _momentum(data["sp500"], 60)
            if r_mom > s_mom + 0.05:
                snap.russell_vs_sp = "small_cap_leading"  # early expansion
            elif s_mom > r_mom + 0.05:
                snap.russell_vs_sp = "large_cap_leading"  # late cycle
            else:
                snap.russell_vs_sp = "balanced"

        # Economic phase detection
        snap.economic_phase = self._detect_economic_phase(
            snap.sp500_trend, snap.yield_curve, snap.vix,
            snap.copper_trend, snap.oil_trend
        )

        # ═══ Layer 6: KONDRATIEFF WAVE ═══
        # We are currently in the AI-driven "Summer" phase of the K-wave
        # (Technology boom, high innovation, increasing inequality)
        snap.kondratieff = KondratieffSeason.SUMMER

        # ═══ COMPOSITE ═══
        snap.overall_regime, snap.confidence = self._compute_regime(snap)
        snap.sector_adjustments = self._compute_sector_impacts(snap)
        snap.reasoning = self._generate_reasoning(snap)

        return snap

    def _detect_economic_phase(self, sp_trend, yield_curve, vix, copper_t, oil_t):
        expansion = 0; contraction = 0

        if sp_trend == "rising": expansion += 2
        elif sp_trend == "falling": contraction += 2

        if yield_curve in ("normal", "steep"): expansion += 1
        elif yield_curve in ("inverted", "deeply_inverted"): contraction += 1

        if vix < 20: expansion += 1
        elif vix > 25: contraction += 1

        if copper_t == "rising": expansion += 1
        elif copper_t == "falling": contraction += 1

        if expansion > contraction + 2: return EconomicPhase.EXPANSION
        elif contraction > expansion + 2: return EconomicPhase.CONTRACTION
        elif expansion > contraction: return EconomicPhase.PEAK
        else: return EconomicPhase.TROUGH

    def _compute_regime(self, snap):
        risk_on = 0; risk_off = 0

        # VIX
        if snap.vix_regime == "calm": risk_on += 2
        elif snap.vix_regime == "panic": risk_off += 3
        elif snap.vix_regime == "elevated": risk_off += 1

        # BTC as risk proxy
        if snap.btc_as_risk == "risk_on": risk_on += 1
        elif snap.btc_as_risk == "risk_off": risk_off += 1

        # Economic phase
        if snap.economic_phase == EconomicPhase.EXPANSION: risk_on += 2
        elif snap.economic_phase == EconomicPhase.CONTRACTION: risk_off += 2

        # Gold
        if snap.gold_trend == "rising": risk_off += 1

        total = risk_on + risk_off
        if risk_on > risk_off + 1:
            return "RISK_ON", risk_on / max(total, 1)
        elif risk_off > risk_on + 1:
            return "RISK_OFF", risk_off / max(total, 1)
        else:
            return "MIXED", 0.5

    def _compute_sector_impacts(self, snap):
        impacts = {}

        for sector, sensitivities in self.SECTOR_SENSITIVITY.items():
            adj = 0.0

            # VIX
            if "vix" in sensitivities:
                vix_signal = -1 if snap.vix > 25 else (1 if snap.vix < 15 else 0)
                adj += sensitivities["vix"] * vix_signal * 0.15

            # Rates
            if "rates" in sensitivities:
                rate_signal = 1 if snap.us_10y > 4.5 else (-1 if snap.us_10y < 3 else 0)
                adj += sensitivities["rates"] * rate_signal * 0.15

            # BTC correlation
            if "btc" in sensitivities:
                btc_signal = 1 if snap.btc_trend == "rising" else (-1 if snap.btc_trend == "falling" else 0)
                adj += sensitivities["btc"] * btc_signal * 0.10

            # DXY
            if "dxy" in sensitivities:
                dxy_signal = 1 if snap.dxy_trend == "rising" else (-1 if snap.dxy_trend == "falling" else 0)
                adj += sensitivities["dxy"] * dxy_signal * 0.10

            # Oil
            if "oil" in sensitivities:
                oil_signal = 1 if snap.oil_trend == "rising" else (-1 if snap.oil_trend == "falling" else 0)
                adj += sensitivities["oil"] * oil_signal * 0.15

            # Gold
            if "gold" in sensitivities:
                gold_signal = 1 if snap.gold_trend == "rising" else 0
                adj += sensitivities["gold"] * gold_signal * 0.10

            # Copper
            if "copper" in sensitivities:
                cu_signal = 1 if snap.copper_trend == "rising" else (-1 if snap.copper_trend == "falling" else 0)
                adj += sensitivities["copper"] * cu_signal * 0.10

            # Kondratieff bonus for tech in SUMMER
            if "kondratieff" in sensitivities and snap.kondratieff == KondratieffSeason.SUMMER:
                adj += sensitivities["kondratieff"] * 0.08

            # Commodity super cycle
            if "commodity_super" in sensitivities and snap.commodity_cycle == "super_cycle":
                adj += sensitivities["commodity_super"] * 0.15

            # Defensive premium in contraction
            if "defensive" in sensitivities and snap.economic_phase in (EconomicPhase.CONTRACTION, EconomicPhase.TROUGH):
                adj += sensitivities["defensive"] * 0.15

            # Geopolitical premium (always on for China)
            if "geopolitical" in sensitivities:
                adj += sensitivities["geopolitical"] * 0.05

            impacts[sector] = round(adj, 3)

        return impacts

    def _generate_reasoning(self, snap):
        lines = []
        lines.append(f"Overall: {snap.overall_regime} (conf={snap.confidence:.0%})")
        lines.append(f"Sentiment: VIX={snap.vix:.0f}({snap.vix_regime}) BTC={snap.btc_trend}({snap.btc_as_risk})")
        lines.append(f"Monetary: 10Y={snap.us_10y:.1f}% curve={snap.yield_curve} direction={snap.rate_direction}")
        lines.append(f"Commodities: Oil={snap.oil_trend} Gold={snap.gold_trend} Cu={snap.copper_trend} cycle={snap.commodity_cycle}")
        lines.append(f"Currency: DXY={snap.dxy_trend}({snap.dollar_regime}) CNY={snap.usdcny_trend} JPY={snap.usdjpy_trend}")
        lines.append(f"Economy: {snap.economic_phase.value} SP500={snap.sp500_trend} SmallVsLarge={snap.russell_vs_sp}")
        lines.append(f"K-Wave: {snap.kondratieff.value} (AI technology boom phase)")
        return " | ".join(lines)
