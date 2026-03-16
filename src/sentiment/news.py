"""
News Aggregator
===============
Aggregate financial news from multiple free RSS/API sources.
No API keys required — uses public RSS feeds and free endpoints.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError


# Free RSS feeds for financial news
RSS_FEEDS = {
    "yahoo_finance": "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US",
    "google_news": "https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en",
    "seeking_alpha": "https://seekingalpha.com/api/sa/combined/{symbol}.xml",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "cnbc": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
}

# General market news feeds (not ticker-specific)
GENERAL_FEEDS = {
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "reuters_business": "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en",
}

# Search-oriented feeds
SEARCH_FEEDS = {
    "google_news": "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en",
}


@dataclass
class NewsArticle:
    """A news article with metadata."""
    title: str
    source: str
    published: str = ""
    link: str = ""
    summary: str = ""
    symbols: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def id(self) -> str:
        """Unique hash for deduplication."""
        return hashlib.md5(f"{self.title}:{self.source}".encode()).hexdigest()[:12]


def _parse_date(date_str: str) -> Optional[datetime]:
    """Best-effort date parsing."""
    if not date_str:
        return None
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


class NewsAggregator:
    """
    Aggregate financial news from multiple free sources.

    Usage:
        agg = NewsAggregator()
        news = agg.get_news("AAPL", limit=10)
        results = agg.search_news("inflation rate hike")
        topics = agg.trending_topics()
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._feeds = RSS_FEEDS.copy()
        self._general_feeds = GENERAL_FEEDS.copy()
        self._search_feeds = SEARCH_FEEDS.copy()

    def _fetch_rss(self, url: str) -> list[dict]:
        """Fetch and parse RSS feed, returning raw items."""
        items = []
        try:
            req = Request(url, headers={"User-Agent": "FinClaw/5.5"})
            with urlopen(req, timeout=self.timeout) as resp:
                xml_data = resp.read().decode("utf-8", errors="replace")
            root = ET.fromstring(xml_data)

            # RSS 2.0
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                desc_el = item.find("description")
                if title_el is not None and title_el.text:
                    items.append({
                        "title": title_el.text.strip(),
                        "link": (link_el.text.strip() if link_el is not None and link_el.text else ""),
                        "published": (pub_el.text.strip() if pub_el is not None and pub_el.text else ""),
                        "summary": (desc_el.text.strip()[:200] if desc_el is not None and desc_el.text else ""),
                    })

            # Atom fallback
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                pub_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
                summary_el = entry.find("atom:summary", ns)
                if title_el is not None and title_el.text:
                    items.append({
                        "title": title_el.text.strip(),
                        "link": (link_el.get("href", "") if link_el is not None else ""),
                        "published": (pub_el.text.strip() if pub_el is not None and pub_el.text else ""),
                        "summary": (summary_el.text.strip()[:200] if summary_el is not None and summary_el.text else ""),
                    })
        except (URLError, ET.ParseError, OSError, TimeoutError):
            pass
        return items

    def get_news(self, symbol: str, limit: int = 20) -> list[dict]:
        """
        Get news for a specific symbol from multiple sources.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "BTCUSDT")
            limit: Maximum articles to return

        Returns:
            List of article dicts with title, source, published, link, summary
        """
        articles: list[NewsArticle] = []
        seen_ids: set = set()

        for name, url_template in self._feeds.items():
            if "{symbol}" in url_template:
                url = url_template.format(symbol=symbol)
            else:
                url = url_template
            raw_items = self._fetch_rss(url)
            for item in raw_items:
                article = NewsArticle(
                    title=item["title"],
                    source=name,
                    published=item.get("published", ""),
                    link=item.get("link", ""),
                    summary=item.get("summary", ""),
                    symbols=[symbol],
                )
                if article.id not in seen_ids:
                    seen_ids.add(article.id)
                    articles.append(article)

        # Sort by date (newest first), with unparseable dates last
        def sort_key(a: NewsArticle):
            dt = _parse_date(a.published)
            return dt or datetime.min.replace(tzinfo=timezone.utc)

        articles.sort(key=sort_key, reverse=True)
        return [a.to_dict() for a in articles[:limit]]

    def search_news(self, query: str, days: int = 7) -> list[dict]:
        """
        Search news by query string.

        Args:
            query: Search query (e.g., "inflation rate hike", "AAPL earnings")
            days: Limit results to last N days

        Returns:
            List of article dicts
        """
        articles: list[NewsArticle] = []
        seen_ids: set = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        for name, url_template in self._search_feeds.items():
            url = url_template.format(query=query.replace(" ", "+"))
            raw_items = self._fetch_rss(url)
            for item in raw_items:
                article = NewsArticle(
                    title=item["title"],
                    source=name,
                    published=item.get("published", ""),
                    link=item.get("link", ""),
                    summary=item.get("summary", ""),
                )
                dt = _parse_date(article.published)
                if dt and dt < cutoff:
                    continue
                if article.id not in seen_ids:
                    seen_ids.add(article.id)
                    articles.append(article)

        return [a.to_dict() for a in articles]

    def trending_topics(self) -> list[dict]:
        """
        Get currently trending financial topics from general market feeds.

        Returns:
            List of dicts with topic, mention_count, sources, sample_headlines
        """
        all_titles: list[str] = []
        for name, url in self._general_feeds.items():
            raw_items = self._fetch_rss(url)
            for item in raw_items:
                all_titles.append(item["title"])

        # Extract trending topics via word frequency
        word_count: dict[str, int] = {}
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
            "to", "for", "of", "and", "or", "but", "not", "with", "from",
            "by", "as", "it", "its", "this", "that", "has", "have", "had",
            "be", "been", "will", "would", "could", "should", "may", "can",
            "do", "does", "did", "new", "says", "said", "after", "over",
        }
        for title in all_titles:
            words = re.findall(r'\b[A-Za-z]{3,}\b', title.lower())
            for w in words:
                if w not in stop_words:
                    word_count[w] = word_count.get(w, 0) + 1

        # Build topic list from most frequent
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        topics = []
        for word, count in sorted_words[:15]:
            if count < 2:
                break
            sample = [t for t in all_titles if word.lower() in t.lower()][:3]
            topics.append({
                "topic": word,
                "mention_count": count,
                "sample_headlines": sample,
            })

        return topics

    def earnings_calendar(self, days_ahead: int = 7) -> list[dict]:
        """
        Get upcoming earnings from free sources.

        Args:
            days_ahead: Number of days to look ahead

        Returns:
            List of dicts with symbol, company, date, estimate info
        """
        # Use Google News RSS as a proxy for earnings announcements
        query = "earnings+report+this+week"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        raw_items = self._fetch_rss(url)

        earnings: list[dict] = []
        ticker_pattern = re.compile(r'\b([A-Z]{1,5})\b')

        for item in raw_items[:30]:
            title = item["title"]
            # Extract potential tickers from headline
            matches = ticker_pattern.findall(title)
            # Filter common non-ticker words
            non_tickers = {"CEO", "IPO", "FDA", "SEC", "ETF", "GDP", "CPI", "NYSE", "AI", "US", "UK", "EU"}
            tickers = [m for m in matches if m not in non_tickers and len(m) >= 2]

            if tickers:
                earnings.append({
                    "symbols": tickers[:3],
                    "headline": title,
                    "source": "google_news",
                    "published": item.get("published", ""),
                })

        return earnings[:20]
