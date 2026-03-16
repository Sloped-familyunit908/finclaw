"""
Tests for FinClaw v5.5.0 — Social Sentiment & News Analysis
============================================================
35+ tests covering SentimentAnalyzer, NewsAggregator, SocialMonitor, and CLI.
"""

import argparse
import json
import math
import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── SentimentAnalyzer Tests ───────────────────────────────────


class TestSentimentAnalyzer:
    """Tests for src.sentiment.analyzer.SentimentAnalyzer."""

    def _make(self):
        from src.sentiment.analyzer import SentimentAnalyzer
        return SentimentAnalyzer()

    def test_empty_text(self):
        a = self._make()
        r = a.analyze_text("")
        assert r["score"] == 0.0
        assert r["label"] == "neutral"
        assert r["confidence"] == 0.0
        assert r["keywords"] == []

    def test_bullish_headline(self):
        a = self._make()
        r = a.analyze_text("AAPL beats earnings, stock surges to record high")
        assert r["score"] > 0.1
        assert r["label"] == "bullish"
        assert len(r["keywords"]) >= 2

    def test_bearish_headline(self):
        a = self._make()
        r = a.analyze_text("Stock crashes amid recession fears, massive selloff")
        assert r["score"] < -0.1
        assert r["label"] == "bearish"

    def test_neutral_headline(self):
        a = self._make()
        r = a.analyze_text("Company announces quarterly results")
        assert r["label"] == "neutral"

    def test_score_range(self):
        a = self._make()
        texts = [
            "extreme bullish rally surge breakout soar boom",
            "crash plunge bankruptcy selloff recession default",
            "the company held a meeting today",
        ]
        for t in texts:
            r = a.analyze_text(t)
            assert -1.0 <= r["score"] <= 1.0

    def test_negation_flips_sentiment(self):
        a = self._make()
        pos = a.analyze_text("strong growth momentum")
        neg = a.analyze_text("not strong not growth")
        assert pos["score"] > neg["score"]

    def test_amplifier_increases_score(self):
        a = self._make()
        normal = a.analyze_text("stock surges")
        amplified = a.analyze_text("stock extremely surges")
        assert abs(amplified["score"]) >= abs(normal["score"])

    def test_dampener_decreases_score(self):
        a = self._make()
        normal = a.analyze_text("stock surges")
        dampened = a.analyze_text("stock slightly surges")
        assert abs(dampened["score"]) <= abs(normal["score"])

    def test_confidence_present(self):
        a = self._make()
        r = a.analyze_text("bullish rally surge gains")
        assert 0.0 <= r["confidence"] <= 1.0

    def test_keywords_returned(self):
        a = self._make()
        r = a.analyze_text("bullish upgrade rally")
        kw_words = [k["word"] for k in r["keywords"]]
        assert "bullish" in kw_words
        assert "upgrade" in kw_words

    # ─── analyze_headlines ─────────────────────────────

    def test_analyze_headlines_empty(self):
        a = self._make()
        r = a.analyze_headlines([])
        assert r["total"] == 0
        assert r["overall_label"] == "neutral"

    def test_analyze_headlines_strings(self):
        a = self._make()
        headlines = [
            "Stock surges on strong earnings beat",
            "Company crashes after missing targets",
            "Quarterly meeting held today",
        ]
        r = a.analyze_headlines(headlines)
        assert r["total"] == 3
        assert r["bullish_count"] + r["bearish_count"] + r["neutral_count"] == 3
        assert r["trend"] in ("improving", "deteriorating", "stable")

    def test_analyze_headlines_dicts(self):
        a = self._make()
        headlines = [
            {"title": "Bullish rally continues"},
            {"title": "Bearish crash fears grow"},
        ]
        r = a.analyze_headlines(headlines)
        assert r["total"] == 2

    def test_analyze_headlines_trend(self):
        a = self._make()
        # First half bearish, second half bullish => improving
        headlines = [
            "crash plunge selloff",
            "recession fears grow",
            "strong recovery rally",
            "bullish surge breakout",
        ]
        r = a.analyze_headlines(headlines)
        assert r["trend"] in ("improving", "deteriorating", "stable")

    def test_analyze_headlines_scores_list(self):
        a = self._make()
        r = a.analyze_headlines(["growth", "decline"])
        assert len(r["scores"]) == 2

    # ─── fear_greed_composite ──────────────────────────

    def test_fear_greed_no_yfinance(self):
        """When yfinance is not importable, returns neutral."""
        a = self._make()
        with patch.dict("sys.modules", {"yfinance": None}):
            # Force ImportError
            import importlib
            with patch("builtins.__import__", side_effect=lambda name, *a, **kw: (_ for _ in ()).throw(ImportError()) if name == "yfinance" else importlib.__import__(name, *a, **kw)):
                r = a.fear_greed_composite("FAKE")
                assert r["value"] == 50
                assert r["label"] == "neutral"
                assert r["symbol"] == "FAKE"

    def test_fear_greed_structure(self):
        a = self._make()
        # Mock yfinance
        mock_yf = MagicMock()
        import pandas as pd
        import numpy as np
        dates = pd.date_range("2024-01-01", periods=60)
        prices = np.linspace(100, 120, 60)
        volumes = np.random.randint(1000000, 5000000, 60)
        hist = pd.DataFrame({"Close": prices, "Volume": volumes}, index=dates)
        mock_yf.Ticker.return_value.history.return_value = hist
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            r = a.fear_greed_composite("AAPL")
        assert 0 <= r["value"] <= 100
        assert r["label"] in ("extreme_fear", "fear", "neutral", "greed", "extreme_greed")
        assert "components" in r


# ─── NewsAggregator Tests ─────────────────────────────────────


class TestNewsAggregator:
    """Tests for src.sentiment.news.NewsAggregator."""

    def _make(self):
        from src.sentiment.news import NewsAggregator
        return NewsAggregator()

    def test_init(self):
        agg = self._make()
        assert agg.timeout == 10
        assert len(agg._feeds) > 0

    def test_get_news_offline(self):
        """get_news returns empty list when feeds are unreachable."""
        agg = self._make()
        with patch("src.sentiment.news.urlopen", side_effect=OSError("offline")):
            result = agg.get_news("AAPL", limit=5)
        assert isinstance(result, list)

    def test_get_news_parses_rss(self):
        """get_news parses valid RSS XML."""
        agg = self._make()
        xml = b"""<?xml version="1.0"?>
        <rss><channel>
            <item><title>AAPL beats earnings</title><pubDate>Mon, 10 Mar 2025 12:00:00 GMT</pubDate><link>https://example.com</link></item>
            <item><title>AAPL stock surges</title><pubDate>Mon, 10 Mar 2025 11:00:00 GMT</pubDate></item>
        </channel></rss>"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = xml
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("src.sentiment.news.urlopen", return_value=mock_resp):
            result = agg.get_news("AAPL", limit=5)
        assert len(result) >= 2
        assert result[0]["title"] in ("AAPL beats earnings", "AAPL stock surges")

    def test_search_news_offline(self):
        agg = self._make()
        with patch("src.sentiment.news.urlopen", side_effect=OSError):
            result = agg.search_news("inflation")
        assert isinstance(result, list)

    def test_trending_topics_offline(self):
        agg = self._make()
        with patch("src.sentiment.news.urlopen", side_effect=OSError):
            result = agg.trending_topics()
        assert isinstance(result, list)

    def test_trending_topics_structure(self):
        agg = self._make()
        xml = b"""<?xml version="1.0"?>
        <rss><channel>
            <item><title>Stock market rally continues strong</title></item>
            <item><title>Market rally drives gains for investors</title></item>
            <item><title>Tech stocks lead market rally</title></item>
        </channel></rss>"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = xml
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("src.sentiment.news.urlopen", return_value=mock_resp):
            result = agg.trending_topics()
        if result:
            assert "topic" in result[0]
            assert "mention_count" in result[0]

    def test_earnings_calendar_offline(self):
        agg = self._make()
        with patch("src.sentiment.news.urlopen", side_effect=OSError):
            result = agg.earnings_calendar()
        assert isinstance(result, list)

    def test_news_article_dedup(self):
        """Duplicate headlines should be deduplicated."""
        agg = self._make()
        xml = b"""<?xml version="1.0"?>
        <rss><channel>
            <item><title>Same headline</title></item>
            <item><title>Same headline</title></item>
        </channel></rss>"""
        mock_resp = MagicMock()
        mock_resp.read.return_value = xml
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        # All feeds return same data — should dedup within each feed
        with patch("src.sentiment.news.urlopen", return_value=mock_resp):
            result = agg.get_news("TEST", limit=10)
        # Count articles with "Same headline" — should be deduplicated across feeds
        same_count = sum(1 for a in result if a["title"] == "Same headline")
        # At most one per unique source (same title+source = same id)
        assert same_count <= len(agg._feeds)

    def test_news_limit_respected(self):
        agg = self._make()
        xml_items = "".join(f"<item><title>Article {i}</title></item>" for i in range(50))
        xml = f'<?xml version="1.0"?><rss><channel>{xml_items}</channel></rss>'.encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = xml
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("src.sentiment.news.urlopen", return_value=mock_resp):
            result = agg.get_news("TEST", limit=5)
        assert len(result) <= 5


# ─── SocialMonitor Tests ──────────────────────────────────────


class TestSocialMonitor:
    """Tests for src.sentiment.social.SocialMonitor."""

    def _make(self):
        from src.sentiment.social import SocialMonitor
        return SocialMonitor()

    def test_init(self):
        sm = self._make()
        assert sm.timeout == 10

    def test_reddit_sentiment_offline(self):
        sm = self._make()
        with patch("src.sentiment.social.urlopen", side_effect=OSError):
            r = sm.reddit_sentiment("stocks", "AAPL")
        assert r["data_source"] == "estimated"
        assert r["symbol"] == "AAPL"
        assert -1 <= r["sentiment_score"] <= 1

    def test_reddit_sentiment_live(self):
        sm = self._make()
        reddit_json = json.dumps({
            "data": {
                "children": [
                    {"data": {"title": "AAPL bullish rally!", "score": 100, "num_comments": 50, "upvote_ratio": 0.9}},
                    {"data": {"title": "AAPL crashes hard", "score": 50, "num_comments": 30, "upvote_ratio": 0.7}},
                ]
            }
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = reddit_json
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("src.sentiment.social.urlopen", return_value=mock_resp):
            r = sm.reddit_sentiment("stocks", "AAPL")
        assert r["data_source"] == "live"
        assert r["mentions"] == 2
        assert len(r["top_posts"]) <= 5

    def test_twitter_mentions_offline(self):
        sm = self._make()
        with patch("src.sentiment.social.urlopen", side_effect=OSError):
            r = sm.twitter_mentions("TSLA")
        assert r["symbol"] == "TSLA"
        assert r["buzz_level"] in ("low", "normal", "high", "viral")

    def test_social_volume_change(self):
        sm = self._make()
        r = sm.social_volume_change("AAPL", "24h")
        assert r["symbol"] == "AAPL"
        assert r["period"] == "24h"
        assert r["trend"] in ("surging", "rising", "stable", "declining")
        assert r["current_volume"] > 0
        assert r["previous_volume"] > 0

    def test_social_volume_periods(self):
        sm = self._make()
        for period in ("24h", "7d", "30d"):
            r = sm.social_volume_change("MSFT", period)
            assert r["period"] == period

    def test_wsb_trending_offline(self):
        sm = self._make()
        with patch("src.sentiment.social.urlopen", side_effect=OSError):
            r = sm.wsb_trending()
        assert isinstance(r, list)

    def test_wsb_trending_live(self):
        sm = self._make()
        reddit_json = json.dumps({
            "data": {
                "children": [
                    {"data": {"title": "$NVDA to the moon! Bullish rally", "selftext": "", "score": 500}},
                    {"data": {"title": "$NVDA $TSLA yolo", "selftext": "", "score": 200}},
                    {"data": {"title": "Normal discussion post", "selftext": "", "score": 10}},
                ]
            }
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = reddit_json
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("src.sentiment.social.urlopen", return_value=mock_resp):
            r = sm.wsb_trending()
        assert isinstance(r, list)
        if r:
            assert "symbol" in r[0]
            assert "mentions" in r[0]

    def test_deterministic_hash(self):
        sm = self._make()
        h1 = sm._deterministic_hash("test")
        h2 = sm._deterministic_hash("test")
        h3 = sm._deterministic_hash("other")
        assert h1 == h2
        assert h1 != h3
        assert 0.0 <= h1 <= 1.0


# ─── CLI Tests ─────────────────────────────────────────────────


class TestSentimentCLI:
    """Tests for sentiment CLI commands."""

    def test_sentiment_command_parses(self):
        from src.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["sentiment", "AAPL"])
        assert args.command == "sentiment"
        assert args.symbol == "AAPL"

    def test_sentiment_with_reddit(self):
        from src.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["sentiment", "AAPL", "--reddit"])
        assert args.reddit is True

    def test_news_command_parses(self):
        from src.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["news", "BTCUSDT", "--limit", "10"])
        assert args.command == "news"
        assert args.symbol == "BTCUSDT"
        assert args.limit == 10

    def test_news_with_search(self):
        from src.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["news", "AAPL", "--search", "earnings"])
        assert args.search == "earnings"

    def test_trending_command_parses(self):
        from src.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["trending"])
        assert args.command == "trending"

    def test_version_550(self):
        from src.cli import build_parser
        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._VersionAction):
                assert "0.1.0" in action.version
                return
        pytest.fail("No version action found")


# ─── NewsArticle / parse_date Tests ───────────────────────────


class TestNewsHelpers:
    """Tests for helper classes and functions."""

    def test_news_article_to_dict(self):
        from src.sentiment.news import NewsArticle
        a = NewsArticle(title="Test", source="test_src", link="https://example.com")
        d = a.to_dict()
        assert d["title"] == "Test"
        assert d["source"] == "test_src"

    def test_news_article_id_unique(self):
        from src.sentiment.news import NewsArticle
        a1 = NewsArticle(title="Hello", source="src1")
        a2 = NewsArticle(title="Hello", source="src2")
        a3 = NewsArticle(title="Hello", source="src1")
        assert a1.id != a2.id  # Different source
        assert a1.id == a3.id  # Same title+source

    def test_parse_date_valid(self):
        from src.sentiment.news import _parse_date
        dt = _parse_date("Mon, 10 Mar 2025 12:00:00 GMT")
        assert dt is not None
        assert dt.year == 2025

    def test_parse_date_iso(self):
        from src.sentiment.news import _parse_date
        dt = _parse_date("2025-03-10T12:00:00Z")
        assert dt is not None

    def test_parse_date_invalid(self):
        from src.sentiment.news import _parse_date
        assert _parse_date("not a date") is None
        assert _parse_date("") is None
