"""
CryptoCompare News Sentiment
=============================
Free API — no key needed for basic news endpoint.
Parses crypto news titles for sentiment using keyword matching.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional
from urllib.request import Request, urlopen


_HEADERS = {
    "User-Agent": "FinClaw/1.0 (sentiment analyzer; +https://github.com/finclaw)"
}

# Crypto-specific positive/negative words
POSITIVE_WORDS = {
    "surge", "surges", "rally", "rallies", "bullish", "gain", "gains",
    "soar", "soars", "breakout", "pump", "moon", "adoption", "launch",
    "partnership", "upgrade", "approval", "milestone", "record", "high",
    "growth", "boost", "recover", "recovery", "integration", "buy",
    "accumulate", "outperform", "inflow", "etf", "institutional",
}

NEGATIVE_WORDS = {
    "crash", "crashes", "dump", "dumps", "bearish", "loss", "losses",
    "plunge", "plunges", "hack", "hacked", "exploit", "rug", "scam",
    "fraud", "ban", "banned", "lawsuit", "sec", "investigation",
    "collapse", "sell", "selloff", "outflow", "fear", "panic",
    "vulnerability", "attack", "warning", "risk", "decline",
}


def _fetch_json(url: str, timeout: int = 10) -> Any:
    req = Request(url, headers=_HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _score_text(text: str) -> float:
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _label_score(score: float) -> str:
    if score > 0.1:
        return "bullish"
    elif score < -0.1:
        return "bearish"
    return "neutral"


class CryptoNewsSentiment:
    """Analyze sentiment from CryptoCompare news API."""

    BASE_URL = "https://min-api.cryptocompare.com/data/v2/news/"

    def __init__(self, fetcher: Optional[Callable] = None):
        self._fetch = fetcher or _fetch_json

    def get_news(self, categories: str = "", limit: int = 50) -> List[Dict]:
        """Fetch latest crypto news articles.

        Args:
            categories: Comma-separated categories (e.g. "BTC,ETH")
            limit: Not directly supported by API but we slice results.
        """
        url = f"{self.BASE_URL}?lang=EN"
        if categories:
            url += f"&categories={categories}"
        data = self._fetch(url)
        articles = []
        for item in data.get("Data", [])[:limit]:
            articles.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "url": item.get("url", ""),
                "categories": item.get("categories", ""),
                "published_on": item.get("published_on", 0),
                "body": item.get("body", "")[:200],
            })
        return articles

    def analyze_crypto(self, symbol: str = "", limit: int = 50) -> Dict:
        """Analyze sentiment for crypto news, optionally filtered by symbol."""
        articles = self.get_news(categories=symbol.upper(), limit=limit)
        if not articles:
            return {
                "symbol": symbol.upper() or "CRYPTO",
                "score": 0.0,
                "label": "neutral",
                "articles_analyzed": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "top_headlines": [],
            }

        scores = [_score_text(a["title"]) for a in articles]
        avg_score = sum(scores) / len(scores)
        avg_score = max(-1.0, min(1.0, avg_score))

        bullish = sum(1 for s in scores if s > 0.1)
        bearish = sum(1 for s in scores if s < -0.1)
        neutral = len(scores) - bullish - bearish

        return {
            "symbol": symbol.upper() or "CRYPTO",
            "score": round(avg_score, 4),
            "label": _label_score(avg_score),
            "articles_analyzed": len(articles),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "top_headlines": [a["title"] for a in articles[:5]],
        }
