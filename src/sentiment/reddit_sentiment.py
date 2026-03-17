"""
Reddit Sentiment Analyzer
=========================
Uses Reddit's public JSON API (no auth needed) to analyze sentiment
from subreddit posts and ticker-specific searches.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.parse import quote
import json


# ── Keyword lexicons ────────────────────────────────────────────

POSITIVE_WORDS = {
    "moon", "mooning", "rocket", "buy", "bullish", "calls", "long",
    "green", "pump", "gain", "gains", "profit", "squeeze", "diamond",
    "hands", "hold", "hodl", "surge", "soar", "breakout", "rally",
    "yolo", "tendies", "lambo", "up", "ath", "undervalued", "cheap",
    "load", "loading", "accumulate", "fire", "fomo",
}

NEGATIVE_WORDS = {
    "crash", "dump", "sell", "bearish", "puts", "short", "red",
    "loss", "losses", "bag", "bagholder", "drill", "drilling",
    "tank", "tanking", "plunge", "rug", "rugpull", "scam", "fraud",
    "overvalued", "bubble", "fear", "panic", "rekt", "rip",
    "dead", "worthless", "broke", "margin", "call", "collapse",
}

# Common ticker pattern: 1-5 uppercase letters, optionally preceded by $
TICKER_RE = re.compile(r"(?<!\w)\$?([A-Z]{1,5})(?!\w)")

# Noise tickers to exclude
NOISE_TICKERS = {
    "I", "A", "AM", "PM", "DD", "CEO", "CFO", "IPO", "ETF", "USA",
    "GDP", "IMO", "LOL", "OMG", "WTF", "ATH", "ATL", "FDA", "SEC",
    "THE", "FOR", "AND", "BUT", "NOT", "YOU", "ALL", "CAN", "HAS",
    "HER", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "OUR",
    "OUT", "OWN", "SAY", "SHE", "TOO", "USE", "WAY", "WHO", "BOT",
    "ARE", "BE", "SO", "NO", "ON", "IF", "MY", "UP", "OR", "IT",
    "DO", "IN", "IS", "TO", "AS", "AT", "BY", "GO", "OF", "AN",
    "WE", "US", "AI", "ANY", "DID", "GET", "GOT", "HAD", "HIM",
    "LET", "PUT", "RUN", "TOP", "TRY", "YET", "BIG", "ONE", "TWO",
    "EOD", "EPS", "EDIT", "YOLO", "HODL", "LMAO", "TLDR", "FOMO",
}

_HEADERS = {
    "User-Agent": "FinClaw/1.0 (sentiment analyzer; +https://github.com/finclaw)"
}


def _fetch_json(url: str, timeout: int = 10) -> Any:
    """Fetch JSON from a URL with a polite User-Agent."""
    req = Request(url, headers=_HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _score_text(text: str) -> float:
    """Return sentiment score in [-1, +1] from keyword matching."""
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


class RedditSentiment:
    """Analyze sentiment from Reddit's public JSON API."""

    def __init__(self, fetcher=None):
        """
        Args:
            fetcher: Optional callable(url) -> dict for dependency injection / testing.
        """
        self._fetch = fetcher or _fetch_json

    def get_subreddit_posts(self, subreddit: str, sort: str = "hot", limit: int = 25) -> List[Dict]:
        """Fetch posts from a subreddit."""
        url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"
        data = self._fetch(url)
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "upvote_ratio": d.get("upvote_ratio", 0.5),
                "url": d.get("url", ""),
                "created_utc": d.get("created_utc", 0),
            })
        return posts

    def search_ticker(self, ticker: str, limit: int = 25) -> List[Dict]:
        """Search Reddit for a specific ticker."""
        q = quote(f"{ticker} stock OR crypto")
        url = f"https://www.reddit.com/search.json?q={q}&sort=relevance&t=week&limit={limit}&raw_json=1"
        data = self._fetch(url)
        posts = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            posts.append({
                "title": d.get("title", ""),
                "score": d.get("score", 0),
                "subreddit": d.get("subreddit", ""),
                "num_comments": d.get("num_comments", 0),
            })
        return posts

    def analyze_ticker(self, ticker: str, limit: int = 25) -> Dict:
        """Get sentiment for a specific ticker from Reddit search."""
        posts = self.search_ticker(ticker, limit=limit)
        if not posts:
            return {
                "ticker": ticker,
                "score": 0.0,
                "label": "neutral",
                "posts_analyzed": 0,
                "mentions": 0,
                "avg_post_score": 0,
            }

        scores = []
        total_upvotes = 0
        for p in posts:
            s = _score_text(p["title"])
            # Weight by Reddit score (engagement)
            weight = max(1, p["score"])
            scores.append(s * weight)
            total_upvotes += p["score"]

        total_weight = sum(max(1, p["score"]) for p in posts)
        weighted_score = sum(scores) / total_weight if total_weight else 0.0
        # Clamp to [-1, 1]
        weighted_score = max(-1.0, min(1.0, weighted_score))

        return {
            "ticker": ticker,
            "score": round(weighted_score, 4),
            "label": _label_score(weighted_score),
            "posts_analyzed": len(posts),
            "mentions": len(posts),
            "avg_post_score": round(total_upvotes / len(posts), 1) if posts else 0,
        }

    def subreddit_buzz(self, subreddit: str, limit: int = 50) -> List[Dict]:
        """Find most-mentioned tickers in a subreddit."""
        posts = self.get_subreddit_posts(subreddit, limit=limit)
        ticker_stats: Dict[str, Dict] = {}

        for p in posts:
            tickers_found = TICKER_RE.findall(p["title"])
            for t in tickers_found:
                t = t.upper()
                if t in NOISE_TICKERS or len(t) < 2:
                    continue
                if t not in ticker_stats:
                    ticker_stats[t] = {"mentions": 0, "total_score": 0, "sentiments": []}
                ticker_stats[t]["mentions"] += 1
                ticker_stats[t]["total_score"] += p["score"]
                ticker_stats[t]["sentiments"].append(_score_text(p["title"]))

        results = []
        for ticker, stats in ticker_stats.items():
            avg_sent = sum(stats["sentiments"]) / len(stats["sentiments"]) if stats["sentiments"] else 0
            results.append({
                "ticker": ticker,
                "mentions": stats["mentions"],
                "total_engagement": stats["total_score"],
                "sentiment_score": round(avg_sent, 4),
                "sentiment_label": _label_score(avg_sent),
            })

        results.sort(key=lambda x: x["mentions"], reverse=True)
        return results
