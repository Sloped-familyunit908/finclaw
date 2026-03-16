"""
LLM-powered Sentiment Analyzer
===============================
Uses LLM providers for deep market news interpretation,
falling back to keyword-based analysis when no LLM is available.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .analyzer import SentimentAnalyzer

logger = logging.getLogger("finclaw.sentiment")


class LLMSentimentAnalyzer:
    """
    Enhanced sentiment analysis using LLM for nuanced market interpretation.
    Falls back to keyword-based SentimentAnalyzer if no LLM provider is available.
    """

    def __init__(self, llm_provider=None):
        self._llm = llm_provider
        self._fallback = SentimentAnalyzer()

    async def _get_llm(self):
        if self._llm is None:
            from src.llm import auto_detect_provider
            self._llm = auto_detect_provider()
        return self._llm

    async def analyze_news(self, headlines: List[str], asset: str = "") -> dict:
        """
        Analyze news headlines with LLM for deep sentiment.
        Falls back to keyword-based if LLM unavailable.
        """
        llm = await self._get_llm()
        if llm is None:
            return self._fallback.analyze_headlines(headlines)

        text = "\n".join(f"- {h}" for h in headlines[:20])
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial sentiment analyst. Analyze these headlines "
                    "and return a JSON object with: overall_score (-1 to 1, bearish to bullish), "
                    "overall_label (bullish/bearish/neutral), key_themes (list of strings), "
                    "market_impact (brief string), and confidence (0 to 1)."
                ),
            },
            {
                "role": "user",
                "content": f"Asset: {asset or 'General Market'}\n\nHeadlines:\n{text}",
            },
        ]

        try:
            result = await llm.chat_json(messages)
            # Merge with keyword counts for completeness
            kw_result = self._fallback.analyze_headlines(headlines)
            result.setdefault("bullish_count", kw_result["bullish_count"])
            result.setdefault("bearish_count", kw_result["bearish_count"])
            result.setdefault("neutral_count", kw_result["neutral_count"])
            result.setdefault("total", kw_result["total"])
            result["source"] = "llm"
            return result
        except Exception as e:
            logger.warning("LLM sentiment failed, falling back to keywords: %s", e)
            result = self._fallback.analyze_headlines(headlines)
            result["source"] = "keyword"
            return result

    async def interpret_event(self, event_text: str, asset: str = "") -> dict:
        """Use LLM to interpret a specific market event."""
        llm = await self._get_llm()
        if llm is None:
            basic = self._fallback.analyze_text(event_text)
            basic["interpretation"] = "LLM not available for deep analysis"
            basic["source"] = "keyword"
            return basic

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial analyst. Analyze this market event and return JSON: "
                    "{ score: -1 to 1, impact: 'high/medium/low', timeframe: 'short/medium/long', "
                    "interpretation: 'brief analysis', action_items: ['list'] }"
                ),
            },
            {
                "role": "user",
                "content": f"Asset: {asset or 'General'}\nEvent: {event_text}",
            },
        ]

        try:
            result = await llm.chat_json(messages)
            result["source"] = "llm"
            return result
        except Exception as e:
            logger.warning("LLM event interpretation failed: %s", e)
            basic = self._fallback.analyze_text(event_text)
            basic["source"] = "keyword"
            return basic
