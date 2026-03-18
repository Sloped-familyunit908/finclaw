"""
Tests for Reddit Sentiment, CryptoCompare News, and Social Buzz Aggregator.
All API calls are mocked.
"""

import pytest
from src.sentiment.reddit_sentiment import RedditSentiment, _score_text, _label_score, NOISE_TICKERS
from src.sentiment.crypto_news import CryptoNewsSentiment
from src.sentiment.social_buzz import SocialBuzzAggregator, _is_crypto


# ── Fixtures: mock Reddit API responses ─────────────────────────

def _mock_reddit_search(url):
    """Mock Reddit search JSON."""
    return {
        "data": {
            "children": [
                {"data": {"title": "AAPL is mooning! Bullish rally incoming 🚀", "score": 150, "subreddit": "stocks", "num_comments": 42}},
                {"data": {"title": "AAPL crash dump sell everything bearish", "score": 30, "subreddit": "stocks", "num_comments": 10}},
                {"data": {"title": "AAPL earnings report tomorrow", "score": 80, "subreddit": "stocks", "num_comments": 25}},
            ]
        }
    }


def _mock_reddit_subreddit(url):
    """Mock subreddit hot posts."""
    return {
        "data": {
            "children": [
                {"data": {"title": "TSLA to the moon! Buy calls now", "score": 500, "num_comments": 200, "upvote_ratio": 0.85, "url": "", "created_utc": 1700000000}},
                {"data": {"title": "GME squeeze is happening again rally", "score": 300, "num_comments": 150, "upvote_ratio": 0.90, "url": "", "created_utc": 1700000100}},
                {"data": {"title": "NVDA crash dump sell puts bearish", "score": 100, "num_comments": 50, "upvote_ratio": 0.70, "url": "", "created_utc": 1700000200}},
                {"data": {"title": "Just a regular post about nothing", "score": 10, "num_comments": 2, "upvote_ratio": 0.50, "url": "", "created_utc": 1700000300}},
            ]
        }
    }


def _mock_reddit_empty(url):
    return {"data": {"children": []}}


def _mock_crypto_news(url):
    """Mock CryptoCompare news."""
    return {
        "Data": [
            {"title": "Bitcoin surges past $100K milestone", "source": "CoinDesk", "url": "https://example.com/1", "categories": "BTC", "published_on": 1700000000, "body": "BTC hits new high..."},
            {"title": "Ethereum hack exploit vulnerability found", "source": "CryptoSlate", "url": "https://example.com/2", "categories": "ETH", "published_on": 1700000100, "body": "Security concern..."},
            {"title": "Solana partnership with major bank adoption", "source": "Decrypt", "url": "https://example.com/3", "categories": "SOL", "published_on": 1700000200, "body": "New partnership..."},
            {"title": "Crypto market update for today", "source": "CoinTelegraph", "url": "https://example.com/4", "categories": "BTC,ETH", "published_on": 1700000300, "body": "Markets are..."},
        ]
    }


def _mock_crypto_empty(url):
    return {"Data": []}


# ── Tests: _score_text ──────────────────────────────────────────

class TestScoreText:
    def test_positive(self):
        assert _score_text("stock is mooning bullish rally") > 0

    def test_negative(self):
        assert _score_text("crash dump sell bearish") < 0

    def test_neutral(self):
        assert _score_text("quarterly earnings report tomorrow") == 0.0

    def test_mixed(self):
        score = _score_text("bullish rally but crash risk")
        assert -1 <= score <= 1


class TestLabelScore:
    def test_bullish(self):
        assert _label_score(0.5) == "bullish"

    def test_bearish(self):
        assert _label_score(-0.5) == "bearish"

    def test_neutral(self):
        assert _label_score(0.0) == "neutral"
        assert _label_score(0.05) == "neutral"


# ── Tests: RedditSentiment ──────────────────────────────────────

class TestRedditSentiment:
    def test_analyze_ticker(self):
        rs = RedditSentiment(fetcher=_mock_reddit_search)
        result = rs.analyze_ticker("AAPL")
        assert result["ticker"] == "AAPL"
        assert result["posts_analyzed"] == 3
        assert -1 <= result["score"] <= 1
        assert result["label"] in ("bullish", "bearish", "neutral")

    def test_analyze_ticker_empty(self):
        rs = RedditSentiment(fetcher=_mock_reddit_empty)
        result = rs.analyze_ticker("XYZ")
        assert result["posts_analyzed"] == 0
        assert result["score"] == 0.0
        assert result["label"] == "neutral"

    def test_subreddit_buzz(self):
        rs = RedditSentiment(fetcher=_mock_reddit_subreddit)
        results = rs.subreddit_buzz("wallstreetbets")
        assert isinstance(results, list)
        tickers = [r["ticker"] for r in results]
        # TSLA and GME should be detected
        assert "TSLA" in tickers or "GME" in tickers
        # Noise should be filtered
        for t in tickers:
            assert t not in NOISE_TICKERS

    def test_subreddit_buzz_empty(self):
        rs = RedditSentiment(fetcher=_mock_reddit_empty)
        results = rs.subreddit_buzz("empty_sub")
        assert results == []

    def test_search_ticker(self):
        rs = RedditSentiment(fetcher=_mock_reddit_search)
        posts = rs.search_ticker("AAPL")
        assert len(posts) == 3
        assert "title" in posts[0]

    def test_get_subreddit_posts(self):
        rs = RedditSentiment(fetcher=_mock_reddit_subreddit)
        posts = rs.get_subreddit_posts("wallstreetbets")
        assert len(posts) == 4
        assert posts[0]["score"] == 500


# ── Tests: CryptoNewsSentiment ──────────────────────────────────

class TestCryptoNewsSentiment:
    def test_get_news(self):
        cn = CryptoNewsSentiment(fetcher=_mock_crypto_news)
        articles = cn.get_news()
        assert len(articles) == 4
        assert articles[0]["source"] == "CoinDesk"

    def test_analyze_crypto(self):
        cn = CryptoNewsSentiment(fetcher=_mock_crypto_news)
        result = cn.analyze_crypto("BTC")
        assert result["symbol"] == "BTC"
        assert result["articles_analyzed"] == 4
        assert -1 <= result["score"] <= 1
        assert result["bullish_count"] + result["bearish_count"] + result["neutral_count"] == 4

    def test_analyze_crypto_empty(self):
        cn = CryptoNewsSentiment(fetcher=_mock_crypto_empty)
        result = cn.analyze_crypto("NOTHING")
        assert result["articles_analyzed"] == 0
        assert result["score"] == 0.0

    def test_top_headlines(self):
        cn = CryptoNewsSentiment(fetcher=_mock_crypto_news)
        result = cn.analyze_crypto()
        assert len(result["top_headlines"]) <= 5


# ── Tests: SocialBuzzAggregator ─────────────────────────────────

class TestSocialBuzzAggregator:
    def test_is_crypto(self):
        assert _is_crypto("BTC") is True
        assert _is_crypto("BTCUSDT") is True
        assert _is_crypto("ETH") is True
        assert _is_crypto("AAPL") is False

    def test_buzz_score_stock(self):
        reddit = RedditSentiment(fetcher=_mock_reddit_search)
        crypto_news = CryptoNewsSentiment(fetcher=_mock_crypto_empty)
        buzz = SocialBuzzAggregator(reddit=reddit, crypto_news=crypto_news)
        result = buzz.get_buzz_score("AAPL")
        assert result["symbol"] == "AAPL"
        assert -1 <= result["overall_score"] <= 1
        assert result["overall_label"] in ("bullish", "bearish", "neutral")
        assert result["buzz_level"] in ("low", "medium", "high")
        assert "reddit" in result["sources"]
        # AAPL is not crypto, so crypto_news should not be a weighted source
        assert "crypto_news" not in result["sources"]

    def test_buzz_score_crypto(self):
        reddit = RedditSentiment(fetcher=_mock_reddit_search)
        crypto_news = CryptoNewsSentiment(fetcher=_mock_crypto_news)
        buzz = SocialBuzzAggregator(reddit=reddit, crypto_news=crypto_news)
        result = buzz.get_buzz_score("BTC")
        assert result["symbol"] == "BTC"
        assert "crypto_news" in result["sources"]
        assert result["sources"]["crypto_news"]["articles_analyzed"] == 4

    def test_buzz_score_all_empty(self):
        reddit = RedditSentiment(fetcher=_mock_reddit_empty)
        crypto_news = CryptoNewsSentiment(fetcher=_mock_crypto_empty)
        buzz = SocialBuzzAggregator(reddit=reddit, crypto_news=crypto_news)
        result = buzz.get_buzz_score("ZZZZZ")
        # Even if finclaw_news returns some data, score should be small
        assert -1 <= result["overall_score"] <= 1
        assert result["buzz_level"] in ("low", "medium", "high")

    def test_buzz_handles_exceptions(self):
        """Ensure aggregator handles API failures gracefully."""
        def _raise(url):
            raise ConnectionError("Network error")

        reddit = RedditSentiment(fetcher=_raise)
        crypto_news = CryptoNewsSentiment(fetcher=_raise)
        buzz = SocialBuzzAggregator(reddit=reddit, crypto_news=crypto_news)
        result = buzz.get_buzz_score("BTC")
        # Should still return a valid result, not crash
        assert -1 <= result["overall_score"] <= 1
        assert result["sources"]["reddit"]["label"] == "unavailable"
