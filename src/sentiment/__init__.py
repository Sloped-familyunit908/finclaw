"""
FinClaw Sentiment Analysis Module
=================================
Social sentiment, news aggregation, and market fear/greed analysis.
"""

from .analyzer import SentimentAnalyzer
from .llm_analyzer import LLMSentimentAnalyzer
from .news import NewsAggregator
from .social import SocialMonitor
from .reddit_sentiment import RedditSentiment
from .crypto_news import CryptoNewsSentiment
from .social_buzz import SocialBuzzAggregator

__all__ = [
    "SentimentAnalyzer",
    "LLMSentimentAnalyzer",
    "NewsAggregator",
    "SocialMonitor",
    "RedditSentiment",
    "CryptoNewsSentiment",
    "SocialBuzzAggregator",
]
