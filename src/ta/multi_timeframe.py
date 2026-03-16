"""Multi-Timeframe Analysis — detect trend alignment and divergences across timeframes."""

from __future__ import annotations

from typing import Any

import numpy as np

from src.ta import sma, ema, rsi, macd, adx


class MultiTimeframeAnalyzer:
    """Analyze price data across multiple timeframes for trend alignment."""

    TIMEFRAMES = ["1h", "4h", "1d", "1w"]

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def analyze(self, data: dict[str, dict[str, np.ndarray]]) -> dict[str, Any]:
        """Analyze *data* keyed by timeframe, each containing 'close', 'high', 'low'.

        Returns:
            trend_alignment: float 0-1 (fraction of timeframes agreeing)
            signals: per-timeframe signal dicts
            dominant_trend: 'bullish' | 'bearish' | 'neutral'
            divergences: list of divergence descriptions
        """
        signals: dict[str, dict[str, Any]] = {}
        trends: list[str] = []

        for tf in self.TIMEFRAMES:
            if tf not in data:
                continue
            tf_data = data[tf]
            close = tf_data.get("close")
            if close is None or len(close) < 30:
                continue
            sig = self._analyze_timeframe(tf_data)
            signals[tf] = sig
            trends.append(sig["trend"])

        if not trends:
            return {
                "trend_alignment": 0.0,
                "signals": {},
                "dominant_trend": "neutral",
                "divergences": [],
            }

        # Count alignment
        bullish = sum(1 for t in trends if t == "bullish")
        bearish = sum(1 for t in trends if t == "bearish")
        total = len(trends)

        if bullish >= bearish:
            dominant = "bullish" if bullish > total / 2 else "neutral"
            alignment = bullish / total
        else:
            dominant = "bearish" if bearish > total / 2 else "neutral"
            alignment = bearish / total

        divergences = self._find_divergences(signals)

        return {
            "trend_alignment": round(alignment, 4),
            "signals": signals,
            "dominant_trend": dominant,
            "divergences": divergences,
        }

    # ------------------------------------------------------------------
    # Single timeframe analysis
    # ------------------------------------------------------------------

    def _analyze_timeframe(self, tf_data: dict[str, np.ndarray]) -> dict[str, Any]:
        close = tf_data["close"]
        high = tf_data.get("high", close)
        low = tf_data.get("low", close)

        # Trend via SMA crossover
        sma_short = sma(close, 10)
        sma_long = sma(close, 30)
        sma_trend = "bullish" if sma_short[-1] > sma_long[-1] else "bearish"

        # MACD
        macd_line, signal_line, hist = macd(close)
        macd_trend = "bullish" if hist[-1] > 0 else "bearish"

        # RSI
        rsi_val = float(rsi(close, 14)[-1])
        rsi_signal = "overbought" if rsi_val > 70 else ("oversold" if rsi_val < 30 else "neutral")

        # ADX for strength
        adx_val = float(adx(high, low, close, 14)[-1]) if len(close) >= 30 else 0.0
        trend_strength = "strong" if adx_val > 25 else "weak"

        # Consensus
        votes = [sma_trend, macd_trend]
        trend = "bullish" if votes.count("bullish") > votes.count("bearish") else "bearish"

        return {
            "trend": trend,
            "sma_trend": sma_trend,
            "macd_trend": macd_trend,
            "rsi": round(rsi_val, 2),
            "rsi_signal": rsi_signal,
            "adx": round(adx_val, 2),
            "trend_strength": trend_strength,
            "momentum": round(float(hist[-1]), 6),
        }

    # ------------------------------------------------------------------
    # Divergences
    # ------------------------------------------------------------------

    @staticmethod
    def _find_divergences(signals: dict[str, dict[str, Any]]) -> list[str]:
        tfs = list(signals.keys())
        if len(tfs) < 2:
            return []
        divergences: list[str] = []

        # Check adjacent timeframes for trend disagreements
        for i in range(len(tfs) - 1):
            a, b = tfs[i], tfs[i + 1]
            if signals[a]["trend"] != signals[b]["trend"]:
                divergences.append(
                    f"{a} ({signals[a]['trend']}) vs {b} ({signals[b]['trend']}): trend divergence"
                )

        # RSI divergence: lower tf overbought while higher tf bearish
        for i in range(len(tfs) - 1):
            lower, higher = tfs[i], tfs[i + 1]
            if signals[lower]["rsi_signal"] == "overbought" and signals[higher]["trend"] == "bearish":
                divergences.append(f"{lower} RSI overbought while {higher} trend bearish")
            elif signals[lower]["rsi_signal"] == "oversold" and signals[higher]["trend"] == "bullish":
                divergences.append(f"{lower} RSI oversold while {higher} trend bullish")

        return divergences
