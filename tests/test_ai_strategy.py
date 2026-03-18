"""
Tests for AI Strategy Engine
=============================
All LLM calls are mocked — no API keys needed.
"""

from __future__ import annotations

import ast
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai_strategy.prompt_templates import (
    build_system_prompt,
    build_user_prompt,
    build_optimization_prompt,
    build_copilot_system_prompt,
    MARKET_CONTEXT,
    RISK_PROFILES,
    STRATEGY_PLUGIN_EXAMPLE,
)
from src.ai_strategy.strategy_generator import (
    StrategyGenerator,
    _extract_python,
    _validate_code,
)
from src.ai_strategy.strategy_optimizer import StrategyOptimizer
from src.ai_strategy.copilot import FinClawCopilot


# ── Prompt Templates ──────────────────────────────────────────

class TestPromptTemplates:
    def test_system_prompt_contains_market(self):
        prompt = build_system_prompt("crypto", "high")
        assert "Cryptocurrency" in prompt or "crypto" in prompt.lower()
        assert "Aggressive" in prompt or "high" in prompt.lower()

    def test_system_prompt_default(self):
        prompt = build_system_prompt()
        assert "StrategyPlugin" in prompt

    def test_user_prompt(self):
        p = build_user_prompt("buy when RSI < 30")
        assert "RSI" in p

    def test_optimization_prompt(self):
        p = build_optimization_prompt("class X: pass", {"sharpe": 1.5, "max_drawdown": -0.15})
        assert "sharpe" in p
        assert "JSON" in p

    def test_copilot_system_prompt(self):
        p = build_copilot_system_prompt()
        assert "Copilot" in p

    def test_all_markets_covered(self):
        for m in ("us_stock", "crypto", "cn_stock"):
            assert m in MARKET_CONTEXT

    def test_all_risk_levels(self):
        for r in ("low", "medium", "high"):
            assert r in RISK_PROFILES

    def test_example_is_valid_python(self):
        tree = ast.parse(STRATEGY_PLUGIN_EXAMPLE)
        assert tree is not None
        assert len(tree.body) > 0, "STRATEGY_PLUGIN_EXAMPLE should contain at least one statement"


# ── Code Extraction & Validation ─────────────────────────────

class TestExtractValidate:
    def test_extract_from_markdown(self):
        raw = "Here is the code:\n```python\nx = 1\n```\nDone."
        assert _extract_python(raw) == "x = 1"

    def test_extract_plain(self):
        assert _extract_python("x = 1") == "x = 1"

    def test_validate_valid_code(self):
        code = '''
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin

class MyStrat(StrategyPlugin):
    name = "test"
    def generate_signals(self, data):
        return pd.Series(0, index=data.index)
    def get_parameters(self):
        return {}
'''
        result = _validate_code(code)
        assert result["valid"]
        assert result["class_name"] == "MyStrat"

    def test_validate_syntax_error(self):
        result = _validate_code("def foo(:\n  pass")
        assert not result["valid"]
        assert any("SyntaxError" in e for e in result["errors"])

    def test_validate_missing_class(self):
        result = _validate_code("x = 1")
        assert not result["valid"]
        assert any("StrategyPlugin" in e for e in result["errors"])

    def test_validate_missing_methods(self):
        code = '''
from src.plugin_system.plugin_types import StrategyPlugin
class Bad(StrategyPlugin):
    pass
'''
        result = _validate_code(code)
        assert not result["valid"]
        assert any("generate_signals" in e for e in result["errors"])


# ── Strategy Generator (mocked LLM) ──────────────────────────

MOCK_STRATEGY_RESPONSE = '''```python
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin

class TestStrategy(StrategyPlugin):
    name = "test_gen"
    version = "1.0.0"
    description = "Test"
    author = "ai"
    risk_level = "medium"
    markets = ["us_stock"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        return pd.Series(0, index=data.index)

    def get_parameters(self) -> dict:
        return {}
```'''


class TestStrategyGenerator:
    def test_generate_success(self):
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=MOCK_STRATEGY_RESPONSE)

        gen = StrategyGenerator(provider=mock_provider)
        result = gen.generate("buy when RSI < 30")

        assert result["valid"]
        assert result["class_name"] == "TestStrategy"
        assert "generate_signals" in result["code"]

    def test_generate_retry_on_bad_code(self):
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(
            side_effect=["invalid python {{{", MOCK_STRATEGY_RESPONSE]
        )

        gen = StrategyGenerator(provider=mock_provider)
        result = gen.generate("buy when RSI < 30")

        assert result["valid"]
        assert mock_provider.chat.call_count == 2

    def test_no_provider_raises(self):
        gen = StrategyGenerator()
        with patch("src.ai_strategy.strategy_generator.auto_detect_provider", return_value=None):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                gen.generate("test")


# ── Strategy Optimizer ────────────────────────────────────────

class TestStrategyOptimizer:
    def test_analyze(self):
        mock_provider = MagicMock()
        mock_provider.chat_json = AsyncMock(return_value={
            "analysis": "Good strategy but overfitting risk",
            "suggestions": [{"parameter": "rsi_period", "current": 14, "suggested": 21, "reason": "smoother"}],
            "code_improvements": "Add volume confirmation",
            "risk_assessment": "medium",
        })

        opt = StrategyOptimizer(provider=mock_provider)
        result = opt.analyze("class X: pass", {"sharpe": 1.2})

        assert "analysis" in result
        assert len(result["suggestions"]) == 1

    def test_grid_search(self):
        opt = StrategyOptimizer()

        def eval_fn(params):
            # Simple mock: higher fast_period = higher score
            return params["fast"] * 0.1

        result = opt.grid_search(
            eval_fn,
            {"fast": [5, 10, 20], "slow": [50, 100]},
            maximize=True,
        )

        assert result["best_params"]["fast"] == 20
        assert len(result["all_results"]) == 6  # 3 * 2

    def test_grid_search_minimize(self):
        opt = StrategyOptimizer()
        result = opt.grid_search(
            lambda p: p["x"] ** 2,
            {"x": [-2, -1, 0, 1, 2]},
            maximize=False,
        )
        assert result["best_params"]["x"] == 0
        assert result["best_score"] == 0


# ── Copilot ───────────────────────────────────────────────────

class TestCopilot:
    def test_chat(self):
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value="AAPL looks bullish based on RSI.")

        copilot = FinClawCopilot(provider=mock_provider)
        response = copilot.chat("Analyze AAPL")

        assert "AAPL" in response
        assert len(copilot.history) == 3  # system + user + assistant

    def test_reset(self):
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value="ok")

        copilot = FinClawCopilot(provider=mock_provider)
        copilot.chat("hello")
        assert len(copilot.history) == 3
        copilot.reset()
        assert len(copilot.history) == 1  # just system

    def test_generate_strategy_from_chat(self):
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value=MOCK_STRATEGY_RESPONSE)

        copilot = FinClawCopilot(provider=mock_provider)
        copilot.chat("Create a momentum strategy")

        code = asyncio.run(copilot.generate_strategy_from_chat_async())
        assert code is not None
        assert "TestStrategy" in code


# ── CLI Integration ───────────────────────────────────────────

class TestCLIIntegration:
    def test_parser_has_generate_strategy(self):
        from src.cli.main import build_parser
        parser = build_parser()
        # Should parse without error
        args = parser.parse_args(["generate-strategy", "buy when RSI < 30", "--market", "crypto"])
        assert args.command == "generate-strategy"
        assert args.market == "crypto"
        assert "RSI" in args.description

    def test_parser_has_optimize_strategy(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["optimize-strategy", "my_strat.py", "--data", "TSLA"])
        assert args.command == "optimize-strategy"
        assert args.data == "TSLA"

    def test_parser_has_copilot(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["copilot"])
        assert args.command == "copilot"
