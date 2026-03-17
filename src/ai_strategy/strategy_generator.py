"""
AI Strategy Generator
=====================
Natural language → StrategyPlugin code, with syntax validation.
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
import textwrap
from typing import Optional

from src.llm.registry import auto_detect_provider, get_provider
from src.llm.base import LLMProvider
from src.ai_strategy.prompt_templates import (
    build_system_prompt,
    build_user_prompt,
)

logger = logging.getLogger("finclaw.ai_strategy")


class StrategyGenerator:
    """Generate StrategyPlugin code from natural language descriptions."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        provider_name: Optional[str] = None,
        market: str = "us_stock",
        risk: str = "medium",
    ):
        self._provider = provider
        self._provider_name = provider_name
        self.market = market
        self.risk = risk

    def _get_provider(self) -> LLMProvider:
        if self._provider:
            return self._provider
        if self._provider_name:
            return get_provider(self._provider_name)
        provider = auto_detect_provider()
        if provider is None:
            raise RuntimeError(
                "No LLM provider available. Set an API key env var "
                "(OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, etc.) "
                "or start a local Ollama instance."
            )
        return provider

    async def generate_async(
        self,
        description: str,
        max_retries: int = 2,
    ) -> dict:
        """
        Generate strategy code from description.

        Returns:
            {"code": str, "class_name": str, "valid": bool, "errors": list[str]}
        """
        provider = self._get_provider()
        system = build_system_prompt(self.market, self.risk)
        user = build_user_prompt(description)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        errors: list[str] = []
        for attempt in range(max_retries + 1):
            try:
                raw = await provider.chat(messages, temperature=0.3)
                code = _extract_python(raw)
                validation = _validate_code(code)

                if validation["valid"]:
                    return {
                        "code": code,
                        "class_name": validation["class_name"],
                        "valid": True,
                        "errors": [],
                    }

                errors = validation["errors"]
                # Ask LLM to fix
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": f"The code has errors: {errors}. Fix them and output only valid Python.",
                })
            except Exception as e:
                errors.append(str(e))

        return {
            "code": code if "code" in dir() else "",
            "class_name": "",
            "valid": False,
            "errors": errors,
        }

    def generate(self, description: str, max_retries: int = 2) -> dict:
        """Sync wrapper for generate_async."""
        return asyncio.run(self.generate_async(description, max_retries))

    async def interactive_async(self) -> str:
        """Interactive multi-turn strategy building. Returns final code."""
        provider = self._get_provider()
        system = build_system_prompt(self.market, self.risk)
        messages = [{"role": "system", "content": system}]

        print("\n  🤖 FinClaw AI Strategy Builder (type 'done' to generate, 'quit' to exit)")
        print("  Describe your strategy idea:\n")

        while True:
            try:
                user_input = input("  You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input:
                continue
            if user_input.lower() == "quit":
                return ""
            if user_input.lower() == "done":
                messages.append({
                    "role": "user",
                    "content": "Now generate the complete StrategyPlugin code based on our discussion.",
                })
                raw = await provider.chat(messages, temperature=0.3)
                code = _extract_python(raw)
                validation = _validate_code(code)
                if validation["valid"]:
                    print(f"\n  ✅ Generated {validation['class_name']}")
                else:
                    print(f"\n  ⚠ Code has issues: {validation['errors']}")
                return code

            messages.append({"role": "user", "content": user_input})
            response = await provider.chat(messages, temperature=0.7)
            messages.append({"role": "assistant", "content": response})
            print(f"\n  🤖: {response}\n")

        return ""


def _extract_python(raw: str) -> str:
    """Extract Python code from LLM response, stripping markdown fences."""
    # Try to find code in ```python ... ``` blocks
    match = re.search(r"```python\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic code blocks
    match = re.search(r"```\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Assume entire response is code
    return raw.strip()


def _validate_code(code: str) -> dict:
    """Validate generated code: syntax + StrategyPlugin structure."""
    errors = []
    class_name = ""

    # 1. Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"valid": False, "class_name": "", "errors": [f"SyntaxError: {e}"]}

    # 2. Find class inheriting from StrategyPlugin
    classes = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(b, ast.Attribute) and b.attr == "StrategyPlugin")
            or (isinstance(b, ast.Name) and b.id == "StrategyPlugin")
            for b in node.bases
        )
    ]
    if not classes:
        errors.append("No class inheriting from StrategyPlugin found")
        return {"valid": False, "class_name": "", "errors": errors}

    cls = classes[0]
    class_name = cls.name

    # 3. Check required methods
    method_names = {
        node.name for node in ast.walk(cls) if isinstance(node, ast.FunctionDef)
    }
    for required in ("generate_signals", "get_parameters"):
        if required not in method_names:
            errors.append(f"Missing required method: {required}")

    return {"valid": len(errors) == 0, "class_name": class_name, "errors": errors}
