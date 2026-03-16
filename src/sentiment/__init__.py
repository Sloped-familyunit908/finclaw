"""
FinClaw Sentiment Analysis Module
=================================
Social sentiment, news aggregation, and market fear/greed analysis.
"""

from .analyzer import SentimentAnalyzer
from .llm_analyzer import LLMSentimentAnalyzer
from .news import NewsAggregator
from .social import SocialMonitor

__all__ = ["SentimentAnalyzer", "LLMSentimentAnalyzer", "NewsAggregator", "SocialMonitor"]
