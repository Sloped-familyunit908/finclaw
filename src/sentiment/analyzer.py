"""
Sentiment Analyzer
==================
Financial text sentiment analysis using keyword lexicons.
No ML dependencies — simple, fast, and effective for headline analysis.
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional


class SentimentAnalyzer:
    """
    Financial sentiment analyzer using curated keyword lexicons.

    Returns scores in [-1, +1] range:
      - Positive = bullish sentiment
      - Negative = bearish sentiment
      - Zero = neutral

    Usage:
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_text("AAPL beats earnings, stock surges 5%")
        # {'score': 0.45, 'label': 'bullish', 'confidence': 0.72, 'keywords': [...]}
    """

    def __init__(self):
        # Financial positive lexicon with weights
        self.positive_words: Dict[str, float] = {
            "growth": 0.3, "beat": 0.5, "beats": 0.5, "strong": 0.3,
            "upgrade": 0.5, "upgraded": 0.5, "momentum": 0.2,
            "bullish": 0.6, "rally": 0.5, "rallies": 0.5, "surge": 0.5,
            "surges": 0.5, "outperform": 0.5, "outperforms": 0.5,
            "breakout": 0.4, "profit": 0.3, "profits": 0.3,
            "record": 0.3, "gain": 0.3, "gains": 0.3,
            "buy": 0.3, "positive": 0.2, "optimistic": 0.3,
            "recovery": 0.4, "expand": 0.2, "expansion": 0.3,
            "exceed": 0.4, "exceeds": 0.4, "exceeded": 0.4,
            "innovation": 0.2, "dividend": 0.2, "revenue": 0.1,
            "soar": 0.5, "soars": 0.5, "jump": 0.4, "jumps": 0.4,
            "boom": 0.4, "booming": 0.4, "upbeat": 0.3,
            "outpace": 0.3, "accelerate": 0.3, "accelerates": 0.3,
            "robust": 0.3, "resilient": 0.3, "rebound": 0.4,
            "rebounds": 0.4, "upside": 0.3, "breakthrough": 0.4,
            "highs": 0.3, "high": 0.2, "overweight": 0.4,
            "accumulate": 0.3, "top": 0.2, "tops": 0.2,
        }

        # Financial negative lexicon with weights
        self.negative_words: Dict[str, float] = {
            "miss": -0.5, "misses": -0.5, "missed": -0.5,
            "weak": -0.3, "weakness": -0.3,
            "downgrade": -0.5, "downgraded": -0.5,
            "risk": -0.2, "risks": -0.2, "risky": -0.3,
            "decline": -0.4, "declines": -0.4, "declining": -0.4,
            "bearish": -0.6, "crash": -0.6, "crashes": -0.6,
            "plunge": -0.5, "plunges": -0.5, "plunging": -0.5,
            "underperform": -0.5, "underperforms": -0.5,
            "sell": -0.3, "selloff": -0.5, "selling": -0.3,
            "loss": -0.4, "losses": -0.4, "lost": -0.3,
            "negative": -0.2, "fear": -0.4, "fears": -0.4,
            "recession": -0.5, "default": -0.5, "defaults": -0.5,
            "bankruptcy": -0.6, "bankrupt": -0.6,
            "warning": -0.4, "warns": -0.4, "warned": -0.4,
            "cut": -0.3, "cuts": -0.3, "concern": -0.3,
            "concerns": -0.3, "volatile": -0.2, "volatility": -0.2,
            "tumble": -0.5, "tumbles": -0.5, "slide": -0.4,
            "slides": -0.4, "slump": -0.5, "slumps": -0.5,
            "layoff": -0.4, "layoffs": -0.4, "shutdown": -0.4,
            "lawsuit": -0.3, "investigation": -0.3,
            "downside": -0.3, "lows": -0.3, "low": -0.2,
            "underweight": -0.4, "overvalued": -0.3,
            "bubble": -0.4, "correction": -0.3, "drop": -0.3,
            "drops": -0.3, "falling": -0.3, "fell": -0.3,
        }

        # Intensity modifiers
        self._amplifiers = {"very", "extremely", "significantly", "sharply", "massively", "hugely"}
        self._dampeners = {"slightly", "somewhat", "marginally", "modestly"}
        self._negators = {"not", "no", "never", "neither", "nor", "hardly", "barely", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "won't"}

    def analyze_text(self, text: str) -> dict:
        """
        Analyze sentiment of a single text.

        Args:
            text: Input text (headline, tweet, article excerpt)

        Returns:
            {
                'score': float,       # -1.0 to 1.0
                'label': str,         # 'bullish', 'bearish', or 'neutral'
                'confidence': float,  # 0.0 to 1.0
                'keywords': list,     # matched keywords with weights
            }
        """
        if not text:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0, "keywords": []}

        words = text.lower().split()
        scores: list[float] = []
        keywords: list[dict] = []
        total_words = len(words)

        for i, word in enumerate(words):
            clean = "".join(c for c in word if c.isalnum())
            if not clean:
                continue

            weight = 0.0
            if clean in self.positive_words:
                weight = self.positive_words[clean]
            elif clean in self.negative_words:
                weight = self.negative_words[clean]
            else:
                continue

            # Check for negation (look back 1-3 words)
            negated = False
            for j in range(max(0, i - 3), i):
                prev = "".join(c for c in words[j] if c.isalnum())
                if prev in self._negators:
                    negated = True
                    break
            if negated:
                weight = -weight * 0.8

            # Check for amplifiers/dampeners
            for j in range(max(0, i - 2), i):
                prev = "".join(c for c in words[j] if c.isalnum())
                if prev in self._amplifiers:
                    weight *= 1.5
                elif prev in self._dampeners:
                    weight *= 0.5

            scores.append(weight)
            keywords.append({"word": clean, "weight": round(weight, 3)})

        if not scores:
            return {"score": 0.0, "label": "neutral", "confidence": 0.0, "keywords": []}

        raw_score = sum(scores) / len(scores)
        score = max(-1.0, min(1.0, raw_score))

        # Confidence based on keyword density and agreement
        keyword_density = len(scores) / max(total_words, 1)
        if len(scores) > 1:
            agreement = 1.0 - (sum(1 for s in scores if (s > 0) != (raw_score > 0)) / len(scores))
        else:
            agreement = 0.7
        confidence = min(1.0, keyword_density * 3 * agreement * min(len(scores), 5) / 3)

        if score > 0.1:
            label = "bullish"
        elif score < -0.1:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "score": round(score, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "keywords": keywords,
        }

    def analyze_headlines(self, headlines: list) -> dict:
        """
        Analyze aggregate sentiment from a list of headlines.

        Args:
            headlines: List of headline strings or dicts with 'title' key

        Returns:
            {
                'overall_score': float,
                'overall_label': str,
                'bullish_count': int,
                'bearish_count': int,
                'neutral_count': int,
                'total': int,
                'trend': str,  # 'improving', 'deteriorating', 'stable'
                'scores': list[float],
            }
        """
        if not headlines:
            return {
                "overall_score": 0.0, "overall_label": "neutral",
                "bullish_count": 0, "bearish_count": 0, "neutral_count": 0,
                "total": 0, "trend": "stable", "scores": [],
            }

        scores: list[float] = []
        bullish = bearish = neutral = 0

        for h in headlines:
            text = h if isinstance(h, str) else h.get("title", "")
            result = self.analyze_text(text)
            s = result["score"]
            scores.append(s)
            if s > 0.1:
                bullish += 1
            elif s < -0.1:
                bearish += 1
            else:
                neutral += 1

        overall = sum(scores) / len(scores)

        # Trend: compare first half vs second half
        mid = len(scores) // 2
        if mid > 0 and len(scores) > 2:
            first_half = sum(scores[:mid]) / mid
            second_half = sum(scores[mid:]) / (len(scores) - mid)
            diff = second_half - first_half
            if diff > 0.05:
                trend = "improving"
            elif diff < -0.05:
                trend = "deteriorating"
            else:
                trend = "stable"
        else:
            trend = "stable"

        if overall > 0.1:
            label = "bullish"
        elif overall < -0.1:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "overall_score": round(overall, 4),
            "overall_label": label,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "total": len(scores),
            "trend": trend,
            "scores": [round(s, 4) for s in scores],
        }

    def fear_greed_composite(self, symbol: str) -> dict:
        """
        Compute a composite Fear & Greed index for a symbol.

        Uses price momentum, volume changes, and volatility as proxies
        (fetched via yfinance if available, otherwise uses heuristics).

        Args:
            symbol: Ticker symbol

        Returns:
            {
                'symbol': str,
                'value': int,           # 0-100 (0=extreme fear, 100=extreme greed)
                'label': str,           # 'extreme_fear'/'fear'/'neutral'/'greed'/'extreme_greed'
                'components': dict,     # Individual component scores
            }
        """
        components = {}

        try:
            import yfinance as yf
            import warnings
            import logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="3mo")

            if hist is not None and len(hist) >= 20:
                closes = hist["Close"].values
                volumes = hist["Volume"].values

                # Price momentum (20-day return normalized to 0-100)
                ret_20d = (closes[-1] / closes[-20] - 1) * 100
                momentum_score = max(0, min(100, 50 + ret_20d * 5))
                components["price_momentum"] = round(momentum_score, 1)

                # Volume trend (recent vs average)
                recent_vol = volumes[-5:].mean()
                avg_vol = volumes[-20:].mean()
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0
                vol_score = max(0, min(100, vol_ratio * 50))
                components["volume"] = round(vol_score, 1)

                # Volatility (lower vol = more greed)
                returns = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes))]
                vol_20d = (sum(r**2 for r in returns[-20:]) / 20) ** 0.5 * math.sqrt(252) * 100
                vol_score = max(0, min(100, 100 - vol_20d * 2))
                components["volatility"] = round(vol_score, 1)

                # Distance from 52-week high
                high_52w = max(closes)
                dist = (closes[-1] / high_52w) * 100
                components["52w_high_proximity"] = round(dist, 1)

                # Composite
                weights = [0.3, 0.2, 0.25, 0.25]
                values = [
                    components["price_momentum"],
                    components["volume"],
                    components["volatility"],
                    components["52w_high_proximity"],
                ]
                composite = sum(w * v for w, v in zip(weights, values))
            else:
                composite = 50.0
                components["note"] = "insufficient_data"
        except ImportError:
            # yfinance not available — return neutral
            composite = 50.0
            components["note"] = "yfinance_not_available"
        except Exception:
            composite = 50.0
            components["note"] = "data_fetch_error"

        value = int(max(0, min(100, composite)))

        if value <= 20:
            label = "extreme_fear"
        elif value <= 40:
            label = "fear"
        elif value <= 60:
            label = "neutral"
        elif value <= 80:
            label = "greed"
        else:
            label = "extreme_greed"

        return {
            "symbol": symbol,
            "value": value,
            "label": label,
            "components": components,
        }
