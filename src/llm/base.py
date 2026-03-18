"""
LLM Provider - Abstract Base
=============================
Unified interface for all LLM providers. All implementations use native HTTP (aiohttp).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    timeout: int = 60
    max_retries: int = 2
    extra: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'openai', 'anthropic')."""
        ...

    @property
    @abstractmethod
    def available_models(self) -> List[str]:
        """List of supported model identifiers."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send chat messages and return the assistant's text response."""
        ...

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> dict:
        """Chat expecting a JSON response. Adds JSON instruction and parses."""
        # Append JSON instruction to last user message
        patched = list(messages)
        if patched and patched[-1]["role"] == "user":
            patched[-1] = {
                **patched[-1],
                "content": patched[-1]["content"] + "\n\nRespond with valid JSON only. No markdown, no explanation.",
            }

        raw = await self.chat(patched, model=model, temperature=temperature)
        # Try to extract JSON from response
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return json.loads(text)

    async def close(self) -> None:
        """Cleanup resources (override if needed)."""
        pass
