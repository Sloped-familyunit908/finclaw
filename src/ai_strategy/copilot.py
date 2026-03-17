"""
FinClaw Copilot — Interactive AI Financial Assistant
====================================================
Chat mode for analysis, strategy creation, and backtest comparison.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Optional

from src.llm.registry import auto_detect_provider, get_provider
from src.llm.base import LLMProvider
from src.ai_strategy.prompt_templates import build_copilot_system_prompt
from src.ai_strategy.strategy_generator import StrategyGenerator, _extract_python, _validate_code

logger = logging.getLogger("finclaw.ai_strategy")


class FinClawCopilot:
    """Conversational financial assistant powered by LLM."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        provider_name: Optional[str] = None,
        market: str = "us_stock",
    ):
        self._provider = provider
        self._provider_name = provider_name
        self.market = market
        self.history: List[Dict[str, str]] = [
            {"role": "system", "content": build_copilot_system_prompt()},
        ]

    def _get_provider(self) -> LLMProvider:
        if self._provider:
            return self._provider
        if self._provider_name:
            return get_provider(self._provider_name)
        provider = auto_detect_provider()
        if provider is None:
            raise RuntimeError("No LLM provider available.")
        return provider

    async def chat_async(self, message: str) -> str:
        """Send a message and get a response."""
        provider = self._get_provider()
        self.history.append({"role": "user", "content": message})
        response = await provider.chat(self.history, temperature=0.7)
        self.history.append({"role": "assistant", "content": response})
        return response

    def chat(self, message: str) -> str:
        """Sync wrapper."""
        return asyncio.run(self.chat_async(message))

    async def generate_strategy_from_chat_async(self) -> Optional[str]:
        """Extract and validate any strategy code from the last assistant message."""
        if not self.history or self.history[-1]["role"] != "assistant":
            return None
        code = _extract_python(self.history[-1]["content"])
        validation = _validate_code(code)
        if validation["valid"]:
            return code
        return None

    def reset(self):
        """Clear conversation history."""
        self.history = [
            {"role": "system", "content": build_copilot_system_prompt()},
        ]

    def run_interactive(self):
        """Run interactive REPL loop."""
        print("\n  🦀 FinClaw Copilot — AI Financial Assistant")
        print("  Type your question or 'quit' to exit.\n")

        loop = asyncio.new_event_loop()
        try:
            while True:
                try:
                    user_input = input("  You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit"):
                    break

                response = loop.run_until_complete(self.chat_async(user_input))
                print(f"\n  🤖: {response}\n")
        finally:
            loop.close()

        print("  Bye! 🦀")
