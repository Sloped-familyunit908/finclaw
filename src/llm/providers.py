"""
LLM Providers - All implementations using native aiohttp HTTP calls.
=====================================================================
Supports: OpenAI (+ Azure), Anthropic, Google Gemini, DeepSeek,
          Kimi/Moonshot, Ollama, Groq, Mistral
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from .base import LLMConfig, LLMProvider

logger = logging.getLogger("finclaw.llm")


class _OpenAICompatibleProvider(LLMProvider):
    """Base for OpenAI-compatible APIs (OpenAI, DeepSeek, Groq, Mistral, Kimi, Ollama)."""

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.config.default_model
        url = f"{self.config.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        # Add extra headers (e.g. Azure api-key)
        headers.update(self.config.extra.get("headers", {}))

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            for attempt in range(self.config.max_retries + 1):
                try:
                    async with session.post(
                        url, json=payload, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    ) as resp:
                        if resp.status == 429 and attempt < self.config.max_retries:
                            import asyncio
                            wait = float(resp.headers.get("Retry-After", 2))
                            await asyncio.sleep(wait)
                            continue
                        resp.raise_for_status()
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                except aiohttp.ClientError as e:
                    if attempt == self.config.max_retries:
                        raise RuntimeError(f"{self.name} API error: {e}") from e


# ──────────────────── Concrete providers ────────────────────


class OpenAIProvider(_OpenAICompatibleProvider):
    """OpenAI GPT models."""

    @property
    def name(self) -> str:
        return "openai"

    @property
    def available_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]


class AzureOpenAIProvider(_OpenAICompatibleProvider):
    """Azure OpenAI — uses api-key header and different URL scheme."""

    @property
    def name(self) -> str:
        return "azure_openai"

    @property
    def available_models(self) -> List[str]:
        return ["gpt-4o", "gpt-4", "gpt-35-turbo"]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        deployment = model or self.config.default_model
        api_version = self.config.extra.get("api_version", "2024-06-01")
        url = f"{self.config.base_url}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key,
        }
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    """Anthropic Claude models — uses Messages API."""

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def available_models(self) -> List[str]:
        return ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.config.default_model
        url = f"{self.config.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
        }

        # Anthropic separates system from messages
        system_text = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_text:
            payload["system"] = system_text

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["content"][0]["text"]


class GeminiProvider(LLMProvider):
    """Google Gemini — uses generateContent REST API."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def available_models(self) -> List[str]:
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        model = model or self.config.default_model
        url = (
            f"{self.config.base_url}/v1beta/models/{model}"
            f":generateContent?key={self.config.api_key}"
        )

        # Convert to Gemini format
        system_text = ""
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            else:
                role = "user" if m["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]


class DeepSeekProvider(_OpenAICompatibleProvider):
    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def available_models(self) -> List[str]:
        return ["deepseek-chat", "deepseek-reasoner"]


class MoonshotProvider(_OpenAICompatibleProvider):
    """Kimi / Moonshot AI."""

    @property
    def name(self) -> str:
        return "moonshot"

    @property
    def available_models(self) -> List[str]:
        return ["moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"]


class OllamaProvider(_OpenAICompatibleProvider):
    """Local Ollama instance."""

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def available_models(self) -> List[str]:
        return ["llama3", "mistral", "codellama", "gemma2"]


class GroqProvider(_OpenAICompatibleProvider):
    @property
    def name(self) -> str:
        return "groq"

    @property
    def available_models(self) -> List[str]:
        return ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"]


class MistralProvider(_OpenAICompatibleProvider):
    @property
    def name(self) -> str:
        return "mistral"

    @property
    def available_models(self) -> List[str]:
        return ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest", "open-mistral-nemo"]
