"""
FinClaw Sentiment Analysis Module
=================================
Social sentiment, news aggregation, and market fear/greed analysis.
"""

from .analyzer import SentimentAnalyzer
from .news import NewsAggregator
from .social import SocialMonitor

__all__ = ["SentimentAnalyzer", "NewsAggregator", "SocialMonitor"]
