"""
Simple keyword-based sentiment analyzer.

Provides a basic sentiment score from text. Designed to be swapped out
for an LLM-based implementation later.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class SimpleSentiment:
    """Keyword-based sentiment analyzer.

    Returns a score in [-1, +1] based on keyword matching.
    """

    BULLISH_WORDS: Dict[str, float] = {
        "growth": 0.3,
        "beat": 0.4,
        "strong": 0.3,
        "upgrade": 0.5,
        "momentum": 0.2,
        "bullish": 0.5,
        "rally": 0.4,
        "surge": 0.4,
        "outperform": 0.4,
        "breakout": 0.3,
        "profit": 0.2,
        "record": 0.3,
        "gain": 0.3,
        "buy": 0.3,
        "positive": 0.2,
        "optimistic": 0.3,
        "recovery": 0.3,
        "expand": 0.2,
        "exceed": 0.3,
        "innovation": 0.2,
    }

    BEARISH_WORDS: Dict[str, float] = {
        "miss": -0.4,
        "weak": -0.3,
        "downgrade": -0.5,
        "risk": -0.2,
        "decline": -0.4,
        "bearish": -0.5,
        "crash": -0.5,
        "plunge": -0.4,
        "underperform": -0.4,
        "sell": -0.3,
        "loss": -0.3,
        "negative": -0.2,
        "fear": -0.3,
        "recession": -0.4,
        "default": -0.4,
        "bankruptcy": -0.5,
        "warning": -0.3,
        "cut": -0.2,
        "concern": -0.2,
        "volatility": -0.2,
    }

    def __init__(
        self,
        bullish_words: Optional[Dict[str, float]] = None,
        bearish_words: Optional[Dict[str, float]] = None,
    ):
        self.bullish = bullish_words or self.BULLISH_WORDS.copy()
        self.bearish = bearish_words or self.BEARISH_WORDS.copy()

    def analyze(self, text: str) -> float:
        """Analyze sentiment of text, returning score in [-1, +1]."""
        if not text:
            return 0.0
        words = text.lower().split()
        score = 0.0
        count = 0
        for word in words:
            # Strip punctuation
            clean = "".join(c for c in word if c.isalnum())
            if clean in self.bullish:
                score += self.bullish[clean]
                count += 1
            elif clean in self.bearish:
                score += self.bearish[clean]
                count += 1
        if count == 0:
            return 0.0
        # Normalize to [-1, 1]
        raw = score / count
        return max(-1.0, min(1.0, raw))

    def analyze_batch(self, texts: List[str]) -> List[float]:
        """Analyze multiple texts."""
        return [self.analyze(t) for t in texts]

    def get_keywords_found(self, text: str) -> Dict[str, float]:
        """Return matched keywords and their weights."""
        if not text:
            return {}
        words = text.lower().split()
        found: Dict[str, float] = {}
        for word in words:
            clean = "".join(c for c in word if c.isalnum())
            if clean in self.bullish:
                found[clean] = self.bullish[clean]
            elif clean in self.bearish:
                found[clean] = self.bearish[clean]
        return found
