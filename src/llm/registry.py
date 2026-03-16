"""
LLM Provider Registry
=====================
Auto-detect available providers from environment variables or config.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

from .base import LLMConfig, LLMProvider
from .providers import (
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

logger = logging.getLogger("finclaw.llm")

# ── env var → (ProviderClass, base_url, default_model) ──
_PROVIDER_DEFS = {
    "openai": {
        "cls": OpenAIProvider,
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
    "azure_openai": {
        "cls": AzureOpenAIProvider,
        "env_key": "AZURE_OPENAI_API_KEY",
        "base_url_env": "AZURE_OPENAI_ENDPOINT",
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "cls": AnthropicProvider,
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-sonnet-20241022",
    },
    "gemini": {
        "cls": GeminiProvider,
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com",
        "default_model": "gemini-2.0-flash",
    },
    "deepseek": {
        "cls": DeepSeekProvider,
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "moonshot": {
        "cls": MoonshotProvider,
        "env_key": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
    },
    "ollama": {
        "cls": OllamaProvider,
        "env_key": None,  # no key needed
        "base_url_env": "OLLAMA_BASE_URL",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
    },
    "groq": {
        "cls": GroqProvider,
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "mistral": {
        "cls": MistralProvider,
        "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
    },
}


def _build_provider(name: str, overrides: Optional[dict] = None) -> Optional[LLMProvider]:
    """Build a provider from env vars, with optional overrides from config."""
    defn = _PROVIDER_DEFS.get(name)
    if not defn:
        return None

    env_key = defn.get("env_key")
    api_key = ""
    if env_key:
        api_key = os.environ.get(env_key, "")
        if not api_key and not overrides:
            return None  # key required but missing

    base_url = os.environ.get(defn.get("base_url_env", ""), "") or defn.get("base_url", "")
    default_model = defn.get("default_model", "")

    if overrides:
        api_key = overrides.get("api_key", api_key)
        base_url = overrides.get("base_url", base_url)
        default_model = overrides.get("default_model", default_model)

    config = LLMConfig(
        api_key=api_key,
        base_url=base_url,
        default_model=default_model,
        extra=overrides or {},
    )
    return defn["cls"](config)


def get_provider(name: str, **kwargs) -> LLMProvider:
    """Get a specific provider by name. Raises ValueError if unavailable."""
    provider = _build_provider(name, overrides=kwargs if kwargs else None)
    if provider is None:
        env_key = _PROVIDER_DEFS.get(name, {}).get("env_key", "?")
        raise ValueError(
            f"Provider '{name}' not available. Set {env_key} environment variable."
        )
    return provider


def auto_detect_provider() -> Optional[LLMProvider]:
    """Return the first available provider based on env vars.
    Priority order: OpenAI > Anthropic > Gemini > DeepSeek > Groq > Mistral > Moonshot > Azure > Ollama
    """
    priority = [
        "openai", "anthropic", "gemini", "deepseek",
        "groq", "mistral", "moonshot", "azure_openai", "ollama",
    ]
    for name in priority:
        provider = _build_provider(name)
        if provider is not None:
            logger.info("Auto-detected LLM provider: %s", name)
            return provider
    return None


def list_providers() -> List[str]:
    """List all available provider names (those with API keys set)."""
    available = []
    for name in _PROVIDER_DEFS:
        if _build_provider(name) is not None:
            available.append(name)
    return available
