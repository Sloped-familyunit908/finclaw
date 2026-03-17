"""
Social Buzz Aggregator
======================
Combines Reddit sentiment, CryptoCompare news, and existing FinClaw
sentiment into a unified "Social Buzz Score".
"""

from __future__ import annotations

from typing import Dict, Optional

from .reddit_sentiment import RedditSentiment
from .crypto_news import CryptoNewsSentiment
from .analyzer import SentimentAnalyzer
from .news import NewsAggregator


# Well-known crypto symbols for routing
CRYPTO_SYMBOLS = {
    "BTC", "ETH", "SOL", "DOGE", "XRP", "ADA", "DOT", "AVAX", "LINK",
    "MATIC", "SHIB", "UNI", "AAVE", "LTC", "BNB", "ATOM", "NEAR",
    "FTM", "ALGO", "ICP", "FIL", "SAND", "MANA", "APE", "ARB", "OP",
    "PEPE", "WIF", "BONK",
}


def _is_crypto(symbol: str) -> bool:
    """Guess if a symbol is crypto."""
    s = symbol.upper().replace("USDT", "").replace("USD", "").replace("-", "")
    return s in CRYPTO_SYMBOLS


class SocialBuzzAggregator:
    """Combine multiple sentiment sources into a unified buzz score."""

    def __init__(
        self,
        reddit: Optional[RedditSentiment] = None,
        crypto_news: Optional[CryptoNewsSentiment] = None,
        analyzer: Optional[SentimentAnalyzer] = None,
        news_agg: Optional[NewsAggregator] = None,
    ):
        self.reddit = reddit or RedditSentiment()
        self.crypto_news = crypto_news or CryptoNewsSentiment()
        self.analyzer = analyzer or SentimentAnalyzer()
        self.news_agg = news_agg or NewsAggregator()

    def get_buzz_score(self, symbol: str) -> Dict:
        """
        Get unified social buzz score for a ticker/crypto.

        Returns dict with:
          - overall_score: [-1, +1] weighted average
          - overall_label: bullish/bearish/neutral
          - sources: individual source results
          - buzz_level: low/medium/high based on engagement
        """
        symbol = symbol.upper().replace("$", "")
        sources = {}
        weights = {}

        # 1. Reddit sentiment
        try:
            reddit_result = self.reddit.analyze_ticker(symbol)
            sources["reddit"] = reddit_result
            if reddit_result["posts_analyzed"] > 0:
                weights["reddit"] = 0.35
        except Exception:
            sources["reddit"] = {"score": 0, "label": "unavailable", "posts_analyzed": 0}

        # 2. CryptoCompare news (for crypto symbols)
        if _is_crypto(symbol):
            try:
                crypto_result = self.crypto_news.analyze_crypto(symbol)
                sources["crypto_news"] = crypto_result
                if crypto_result["articles_analyzed"] > 0:
                    weights["crypto_news"] = 0.30
            except Exception:
                sources["crypto_news"] = {"score": 0, "label": "unavailable", "articles_analyzed": 0}

        # 3. Existing FinClaw news sentiment
        try:
            news_articles = self.news_agg.get_news(symbol, limit=20)
            if news_articles:
                headlines = [a["title"] for a in news_articles]
                news_result = self.analyzer.analyze_headlines(headlines)
                sources["finclaw_news"] = news_result
                if news_result.get("total", 0) > 0:
                    weights["finclaw_news"] = 0.35
            else:
                sources["finclaw_news"] = {"overall_score": 0, "overall_label": "neutral", "total": 0}
        except Exception:
            sources["finclaw_news"] = {"overall_score": 0, "overall_label": "neutral", "total": 0}

        # Weighted average
        if not weights:
            overall_score = 0.0
        else:
            total_weight = sum(weights.values())
            overall_score = 0.0
            for src, w in weights.items():
                if src == "finclaw_news":
                    overall_score += sources[src].get("overall_score", 0) * (w / total_weight)
                else:
                    overall_score += sources[src].get("score", 0) * (w / total_weight)

        overall_score = max(-1.0, min(1.0, round(overall_score, 4)))

        # Buzz level from total engagement
        total_items = (
            sources.get("reddit", {}).get("posts_analyzed", 0)
            + sources.get("crypto_news", {}).get("articles_analyzed", 0)
            + sources.get("finclaw_news", {}).get("total", 0)
        )
        if total_items >= 30:
            buzz_level = "high"
        elif total_items >= 10:
            buzz_level = "medium"
        else:
            buzz_level = "low"

        label = "bullish" if overall_score > 0.1 else ("bearish" if overall_score < -0.1 else "neutral")

        return {
            "symbol": symbol,
            "overall_score": overall_score,
            "overall_label": label,
            "buzz_level": buzz_level,
            "total_data_points": total_items,
            "sources": sources,
        }
