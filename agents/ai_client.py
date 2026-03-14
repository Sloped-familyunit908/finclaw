"""
WhaleTrader - AI Client
Unified AI interface supporting multiple LLM providers.
2026 state-of-the-art: Claude 4, GPT-5, DeepSeek-V3, Gemini 2, local Ollama.

Key insight from competitive analysis:
- ai-hedge-fund uses OpenAI/Anthropic/Groq/DeepSeek/Ollama — we support ALL of them
- FinRL-DeepSeek only uses DeepSeek for sentiment — we use LLMs for REASONING
- freqtrade uses ML (FreqAI) but no LLMs — we're the first to combine both
"""

import json
import os
import asyncio
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod


@dataclass
class AIResponse:
    content: str
    model: str
    usage: dict  # tokens used
    raw: dict    # raw API response


class AIClient(ABC):
    """Abstract AI client interface"""
    
    @abstractmethod
    async def chat(self, system: str, message: str, 
                   temperature: float = 0.7, max_tokens: int = 2000) -> str:
        pass

    @abstractmethod
    async def chat_json(self, system: str, message: str,
                        temperature: float = 0.3) -> dict:
        """Chat with guaranteed JSON response"""
        pass


class ClaudeClient(AIClient):
    """Anthropic Claude client — our primary AI"""
    
    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def chat(self, system: str, message: str,
                   temperature: float = 0.7, max_tokens: int = 2000) -> str:
        session = await self._get_session()
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": message}],
        }
        async with session.post(
            f"{self.base_url}/messages", headers=headers, json=payload
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"Claude API error: {data}")
            return data["content"][0]["text"]

    async def chat_json(self, system: str, message: str,
                        temperature: float = 0.3) -> dict:
        response = await self.chat(
            system=system + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation.",
            message=message,
            temperature=temperature,
        )
        # Try to extract JSON from response
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


class OpenAIClient(AIClient):
    """OpenAI GPT client"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def chat(self, system: str, message: str,
                   temperature: float = 0.7, max_tokens: int = 2000) -> str:
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with session.post(
            f"{self.base_url}/chat/completions", headers=headers, json=payload
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"OpenAI API error: {data}")
            return data["choices"][0]["message"]["content"]

    async def chat_json(self, system: str, message: str,
                        temperature: float = 0.3) -> dict:
        response = await self.chat(
            system=system, message=message, temperature=temperature
        )
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    async def close(self):
        if self._session:
            await self._session.close()


class OllamaClient(AIClient):
    """Local Ollama client — free, no API key needed"""
    
    def __init__(self, model: str = "llama3.1", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def chat(self, system: str, message: str,
                   temperature: float = 0.7, max_tokens: int = 2000) -> str:
        session = await self._get_session()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with session.post(
            f"{self.base_url}/api/chat", json=payload
        ) as resp:
            data = await resp.json()
            return data["message"]["content"]

    async def chat_json(self, system: str, message: str,
                        temperature: float = 0.3) -> dict:
        response = await self.chat(
            system=system + "\nRespond with valid JSON only.",
            message=message, temperature=temperature
        )
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    async def close(self):
        if self._session:
            await self._session.close()


class AzureOpenAIClient(AIClient):
    """Azure OpenAI client — uses kazhou's $150/month Azure credits"""
    
    def __init__(self, endpoint: str = None, api_key: str = None,
                 deployment: str = "gpt-4o", api_version: str = "2024-02-15-preview"):
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = deployment
        self.api_version = api_version
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
        return self._session

    async def chat(self, system: str, message: str,
                   temperature: float = 0.7, max_tokens: int = 2000) -> str:
        session = await self._get_session()
        url = (f"{self.endpoint}/openai/deployments/{self.deployment}"
               f"/chat/completions?api-version={self.api_version}")
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"Azure OpenAI error: {data}")
            return data["choices"][0]["message"]["content"]

    async def chat_json(self, system: str, message: str,
                        temperature: float = 0.3) -> dict:
        response = await self.chat(
            system=system, message=message, temperature=temperature
        )
        text = response.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)

    async def close(self):
        if self._session:
            await self._session.close()


def create_client(provider: str = None, **kwargs) -> AIClient:
    """
    Factory: create AI client based on available API keys.
    Auto-detects the best available provider.
    
    Priority: Azure (free credits) > Claude > OpenAI > Ollama (fallback)
    """
    if provider:
        providers = {
            "claude": ClaudeClient,
            "anthropic": ClaudeClient,
            "openai": OpenAIClient,
            "ollama": OllamaClient,
            "azure": AzureOpenAIClient,
        }
        if provider.lower() in providers:
            return providers[provider.lower()](**kwargs)
        raise ValueError(f"Unknown provider: {provider}")

    # Auto-detect
    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureOpenAIClient(**kwargs)
    if os.getenv("ANTHROPIC_API_KEY"):
        return ClaudeClient(**kwargs)
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIClient(**kwargs)
    
    # Fallback to Ollama (local, free)
    return OllamaClient(**kwargs)
