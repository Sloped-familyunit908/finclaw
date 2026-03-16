"""
Tests for the unified LLM provider layer.
Uses mock HTTP responses — no real API keys needed.
"""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.llm.base import LLMConfig, LLMProvider
from src.llm.providers import (
    AnthropicProvider,
    AzureOpenAIProvider,
    DeepSeekProvider,
    GeminiProvider,
    GroqProvider,
    MistralProvider,
    MoonshotProvider,
    OllamaProvider,
    OpenAIProvider,
)
from src.llm.registry import auto_detect_provider, get_provider, list_providers


# ── Helper ──

def _config(api_key="test-key", base_url="https://test.example.com", model="test-model"):
    return LLMConfig(api_key=api_key, base_url=base_url, default_model=model)


MESSAGES = [{"role": "user", "content": "Hello"}]


# ── Base tests ──


class TestLLMConfig:
    def test_defaults(self):
        c = LLMConfig()
        assert c.api_key == ""
        assert c.timeout == 60
        assert c.max_retries == 2


# ── Provider identity ──


class TestProviderNames:
    @pytest.mark.parametrize(
        "cls,expected",
        [
            (OpenAIProvider, "openai"),
            (AnthropicProvider, "anthropic"),
            (GeminiProvider, "gemini"),
            (DeepSeekProvider, "deepseek"),
            (MoonshotProvider, "moonshot"),
            (OllamaProvider, "ollama"),
            (GroqProvider, "groq"),
            (MistralProvider, "mistral"),
            (AzureOpenAIProvider, "azure_openai"),
        ],
    )
    def test_provider_name(self, cls, expected):
        p = cls(_config())
        assert p.name == expected

    @pytest.mark.parametrize(
        "cls",
        [OpenAIProvider, AnthropicProvider, GeminiProvider, DeepSeekProvider,
         MoonshotProvider, OllamaProvider, GroqProvider, MistralProvider],
    )
    def test_available_models_not_empty(self, cls):
        p = cls(_config())
        assert len(p.available_models) > 0


# ── Mock HTTP tests ──


def _mock_openai_response(content="Hello!"):
    """Create a mock aiohttp response for OpenAI-compatible APIs."""
    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={
        "choices": [{"message": {"content": content}}]
    })
    return resp


def _mock_anthropic_response(content="Hello!"):
    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={
        "content": [{"text": content}]
    })
    return resp


def _mock_gemini_response(content="Hello!"):
    resp = AsyncMock()
    resp.status = 200
    resp.raise_for_status = MagicMock()
    resp.json = AsyncMock(return_value={
        "candidates": [{"content": {"parts": [{"text": content}]}}]
    })
    return resp


def _patch_aiohttp(mock_resp):
    """Create a properly configured aiohttp mock context manager."""
    # mock_resp is the response from session.post().__aenter__()
    post_cm = MagicMock()
    post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    post_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.post.return_value = post_cm

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    return patch("aiohttp.ClientSession", return_value=session_cm), session


class TestOpenAIChat:
    @pytest.mark.asyncio
    async def test_chat(self):
        provider = OpenAIProvider(_config(base_url="https://api.openai.com/v1"))
        mock_resp = _mock_openai_response("Hi there!")
        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await provider.chat(MESSAGES)
            assert result == "Hi there!"


class TestAnthropicChat:
    @pytest.mark.asyncio
    async def test_chat(self):
        provider = AnthropicProvider(_config(base_url="https://api.anthropic.com"))
        mock_resp = _mock_anthropic_response("Claude says hi")
        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await provider.chat(MESSAGES)
            assert result == "Claude says hi"

    @pytest.mark.asyncio
    async def test_system_message_extracted(self):
        provider = AnthropicProvider(_config(base_url="https://api.anthropic.com"))
        mock_resp = _mock_anthropic_response("ok")
        patcher, session = _patch_aiohttp(mock_resp)
        with patcher:
            msgs = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hi"},
            ]
            await provider.chat(msgs)

            call_args = session.post.call_args
            payload = call_args[1].get("json") or call_args.kwargs.get("json")
            assert "system" in payload
            assert payload["system"] == "You are helpful"
            for m in payload["messages"]:
                assert m["role"] != "system"


class TestGeminiChat:
    @pytest.mark.asyncio
    async def test_chat(self):
        provider = GeminiProvider(_config(base_url="https://generativelanguage.googleapis.com"))
        mock_resp = _mock_gemini_response("Gemini response")
        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await provider.chat(MESSAGES)
            assert result == "Gemini response"


class TestChatJson:
    @pytest.mark.asyncio
    async def test_chat_json_parses(self):
        provider = OpenAIProvider(_config(base_url="https://api.openai.com/v1"))
        json_content = '{"signal": "buy", "confidence": 0.8}'
        mock_resp = _mock_openai_response(json_content)
        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await provider.chat_json(MESSAGES)
            assert result["signal"] == "buy"
            assert result["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_chat_json_strips_markdown(self):
        provider = OpenAIProvider(_config(base_url="https://api.openai.com/v1"))
        content = '```json\n{"result": true}\n```'
        mock_resp = _mock_openai_response(content)
        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await provider.chat_json(MESSAGES)
            assert result["result"] is True


# ── Registry tests ──


class TestRegistry:
    def test_get_provider_with_explicit_key(self):
        p = get_provider("openai", api_key="sk-test123")
        assert p.name == "openai"

    def test_get_provider_missing_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear all relevant keys
            for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                       "DEEPSEEK_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
                       "MOONSHOT_API_KEY", "AZURE_OPENAI_API_KEY"]:
                os.environ.pop(k, None)
            with pytest.raises(ValueError, match="not available"):
                get_provider("openai")

    def test_auto_detect_with_openai_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            p = auto_detect_provider()
            assert p is not None
            assert p.name == "openai"

    def test_list_providers_with_env(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk-test"}, clear=False):
            providers = list_providers()
            assert "groq" in providers


# ── Agent integration test ──


class TestAgentLLMIntegration:
    @pytest.mark.asyncio
    async def test_momentum_agent_with_mock_llm(self):
        from src.agents.momentum import MomentumAgent
        from src.agents.base import MarketData
        from src.llm.providers import OpenAIProvider

        mock_llm = OpenAIProvider(_config())
        agent = MomentumAgent(ai_client=mock_llm)

        json_resp = json.dumps({
            "signal": "buy",
            "confidence": 0.75,
            "reasoning": "Strong uptrend confirmed by RSI and MACD",
            "key_factors": ["RSI above 50", "MACD crossover"],
            "price_target": 155.0,
            "stop_loss": 140.0,
            "time_horizon": "short",
        })
        mock_resp = _mock_openai_response(json_resp)

        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            market_data = MarketData(
                asset="AAPL",
                current_price=150.0,
                price_24h_ago=148.0,
                price_7d_ago=145.0,
                price_30d_ago=140.0,
                volume_24h=50_000_000,
                high_24h=151.0,
                low_24h=147.0,
                rsi_14=55.0,
                macd=0.5,
                macd_signal=0.3,
                sma_20=148.0,
                sma_50=145.0,
                sma_200=135.0,
            )

            analysis = await agent.analyze("AAPL", market_data)
            assert analysis.signal.value == "buy"
            assert analysis.confidence == 0.75
            assert analysis.price_target == 155.0


# ── Sentiment LLM integration test ──


class TestLLMSentiment:
    @pytest.mark.asyncio
    async def test_analyze_news_with_llm(self):
        from src.sentiment.llm_analyzer import LLMSentimentAnalyzer
        from src.llm.providers import OpenAIProvider

        mock_llm = OpenAIProvider(_config())
        analyzer = LLMSentimentAnalyzer(llm_provider=mock_llm)

        json_resp = json.dumps({
            "overall_score": 0.6,
            "overall_label": "bullish",
            "key_themes": ["earnings beat", "AI growth"],
            "market_impact": "Positive near-term catalyst",
            "confidence": 0.8,
        })
        mock_resp = _mock_openai_response(json_resp)

        patcher, _ = _patch_aiohttp(mock_resp)
        with patcher:
            result = await analyzer.analyze_news(
                ["AAPL beats earnings", "AI revenue surges"],
                asset="AAPL",
            )
            assert result["overall_label"] == "bullish"
            assert result["source"] == "llm"

    @pytest.mark.asyncio
    async def test_fallback_to_keywords(self):
        from src.sentiment.llm_analyzer import LLMSentimentAnalyzer

        analyzer = LLMSentimentAnalyzer(llm_provider=None)
        # With no LLM and no env vars, should fall back
        with patch.dict(os.environ, {}, clear=True):
            for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
                os.environ.pop(k, None)
            result = await analyzer.analyze_news(["Stock surges on earnings beat"])
            assert "overall_score" in result
