"""
News Sentiment Pipeline
=======================
Fetch financial news headlines via RSS and analyze sentiment
using keyword-based scoring. No API keys required.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

from .sentiment import SimpleSentiment


# Free RSS feeds for financial news
DEFAULT_RSS_FEEDS = {
    "yahoo_finance": "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "google_news": "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en",
    "seeking_alpha": "https://seekingalpha.com/api/sa/combined/{ticker}.xml",
}


@dataclass
class Headline:
    """A single news headline."""
    title: str
    source: str
    published: str = ""
    link: str = ""
    sentiment: float = 0.0


class NewsSentimentPipeline:
    """
    Fetch and analyze financial news sentiment from RSS feeds.

    Usage:
        pipeline = NewsSentimentPipeline()
        signal = pipeline.get_signal("AAPL")
        # {'ticker': 'AAPL', 'sentiment': 0.15, 'headlines': 12, 'signal': 'bullish'}
    """

    def __init__(
        self,
        sources: Optional[list[str]] = None,
        feeds: Optional[dict[str, str]] = None,
        timeout: int = 10,
    ):
        self.sources = sources or ["rss"]
        self.feeds = feeds or DEFAULT_RSS_FEEDS
        self.timeout = timeout
        self.analyzer = SimpleSentiment()

    def fetch_headlines(self, ticker: str) -> list[dict]:
        """
        Fetch headlines for a ticker from all configured RSS feeds.
        Returns list of dicts with 'title', 'source', 'published', 'link'.
        """
        headlines: list[dict] = []

        for name, url_template in self.feeds.items():
            try:
                url = url_template.format(ticker=ticker)
                req = Request(url, headers={"User-Agent": "FinClaw/2.1"})
                with urlopen(req, timeout=self.timeout) as resp:
                    xml_data = resp.read().decode("utf-8", errors="replace")

                root = ET.fromstring(xml_data)
                # Standard RSS 2.0
                for item in root.iter("item"):
                    title_el = item.find("title")
                    link_el = item.find("link")
                    pub_el = item.find("pubDate")
                    if title_el is not None and title_el.text:
                        headlines.append({
                            "title": title_el.text.strip(),
                            "source": name,
                            "published": pub_el.text.strip() if pub_el is not None and pub_el.text else "",
                            "link": link_el.text.strip() if link_el is not None and link_el.text else "",
                        })
                # Atom format fallback
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    link_el = entry.find("atom:link", ns)
                    pub_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
                    if title_el is not None and title_el.text:
                        headlines.append({
                            "title": title_el.text.strip(),
                            "source": name,
                            "published": pub_el.text.strip() if pub_el is not None and pub_el.text else "",
                            "link": link_el.get("href", "") if link_el is not None else "",
                        })
            except (URLError, ET.ParseError, OSError, TimeoutError):
                # Feed unavailable — skip silently
                continue

        return headlines

    def analyze_sentiment(self, headlines: list[dict]) -> float:
        """
        Analyze aggregate sentiment from a list of headlines.
        Returns score in [-1.0, +1.0].
        """
        if not headlines:
            return 0.0

        scores = []
        for h in headlines:
            title = h.get("title", "")
            score = self.analyzer.analyze(title)
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    def get_signal(self, ticker: str) -> dict:
        """
        End-to-end: fetch headlines, analyze sentiment, return signal.

        Returns:
            {
                'ticker': str,
                'sentiment': float,  # [-1, 1]
                'headlines': int,
                'signal': 'bullish' | 'bearish' | 'neutral',
                'top_headlines': list[dict],
            }
        """
        headlines = self.fetch_headlines(ticker)
        score = self.analyze_sentiment(headlines)

        if score > 0.1:
            signal = "bullish"
        elif score < -0.1:
            signal = "bearish"
        else:
            signal = "neutral"

        # Annotate individual headline sentiments
        top = []
        for h in headlines[:10]:
            h_copy = dict(h)
            h_copy["sentiment"] = self.analyzer.analyze(h.get("title", ""))
            top.append(h_copy)

        return {
            "ticker": ticker,
            "sentiment": round(score, 4),
            "headlines": len(headlines),
            "signal": signal,
            "top_headlines": top,
        }
