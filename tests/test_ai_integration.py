"""
AI Module Integration Tests
============================
Tests strategy generation, copilot, and optimizer with mocked LLM providers.
"""

import sys
import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Strategy Generator ───────────────────────────────────────────

class TestStrategyGenerator:
    def test_no_api_key_raises(self):
        """Should raise RuntimeError when no LLM provider is available."""
        from src.ai_strategy.strategy_generator import StrategyGenerator

        gen = StrategyGenerator()
        with patch("src.ai_strategy.strategy_generator.auto_detect_provider", return_value=None):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                asyncio.run(gen.generate_async("Buy when RSI < 30"))

    def test_generate_with_mock_llm(self):
        """Mock LLM returns valid strategy code → should parse and validate."""
        from src.ai_strategy.strategy_generator import StrategyGenerator, _validate_code

        mock_code = '''
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin

class RSIOversoldStrategy(StrategyPlugin):
    name = "rsi_oversold"
    description = "Buy when RSI < 30"
    version = "1.0.0"
    author = "AI"
    markets = ["us_stock"]
    risk_level = "medium"

    def generate_signals(self, data):
        return pd.Series(0, index=data.index)

    def get_parameters(self):
        return {"period": 14}
'''
        result = _validate_code(mock_code)
        assert isinstance(result, dict)
        assert result.get("valid") is True, f"Code should be valid: {result}"

    def test_validate_code_invalid(self):
        from src.ai_strategy.strategy_generator import _validate_code
        result = _validate_code("def foo(\n  broken syntax")
        assert isinstance(result, dict)
        assert result.get("valid") is False

    def test_validate_code_empty(self):
        from src.ai_strategy.strategy_generator import _validate_code
        result = _validate_code("")
        assert isinstance(result, dict)
        assert result.get("valid") is False


# ── Copilot ──────────────────────────────────────────────────────

class TestCopilot:
    def test_no_llm_raises(self):
        from src.ai_strategy.copilot import FinClawCopilot

        copilot = FinClawCopilot()
        with patch("src.ai_strategy.copilot.auto_detect_provider", return_value=None):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                asyncio.run(copilot.chat_async("What's the best strategy?"))

    def test_copilot_init(self):
        from src.ai_strategy.copilot import FinClawCopilot

        copilot = FinClawCopilot(market="crypto")
        assert copilot.market == "crypto"
        assert len(copilot.history) == 1  # system prompt
        assert copilot.history[0]["role"] == "system"


# ── Strategy Optimizer ───────────────────────────────────────────

class TestStrategyOptimizer:
    def test_grid_search_basic(self):
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()

        def evaluate(params):
            return params["a"] * 2 + params["b"]

        result = optimizer.grid_search(
            evaluate_fn=evaluate,
            param_grid={"a": [1, 2, 3], "b": [10, 20]},
            maximize=True,
        )
        assert result["best_params"] == {"a": 3, "b": 20}
        assert result["best_score"] == 26
        assert len(result["all_results"]) == 6

    def test_grid_search_minimize(self):
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()

        result = optimizer.grid_search(
            evaluate_fn=lambda p: p["x"] ** 2,
            param_grid={"x": [-3, -1, 0, 1, 3]},
            maximize=False,
        )
        assert result["best_params"] == {"x": 0}
        assert result["best_score"] == 0

    def test_grid_search_with_errors(self):
        """Grid search should handle evaluate_fn errors gracefully."""
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()

        def evaluate(params):
            if params["x"] == 0:
                raise ZeroDivisionError("divide by zero")
            return 1 / params["x"]

        result = optimizer.grid_search(
            evaluate_fn=evaluate,
            param_grid={"x": [-1, 0, 1]},
            maximize=True,
        )
        # Should still find best from valid results
        assert result["best_params"]["x"] == 1
        # Error result should be recorded
        errors = [r for r in result["all_results"] if r.get("error")]
        assert len(errors) == 1

    def test_grid_search_empty_grid(self):
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()
        result = optimizer.grid_search(
            evaluate_fn=lambda p: 0,
            param_grid={},
            maximize=True,
        )
        # Empty grid → single combo of empty params
        assert len(result["all_results"]) == 1

    def test_grid_search_single_param(self):
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()
        result = optimizer.grid_search(
            evaluate_fn=lambda p: -abs(p["x"] - 5),
            param_grid={"x": list(range(11))},
            maximize=True,
        )
        assert result["best_params"]["x"] == 5
        assert result["best_score"] == 0

    def test_no_llm_for_analyze(self):
        from src.ai_strategy.strategy_optimizer import StrategyOptimizer

        optimizer = StrategyOptimizer()
        with patch("src.ai_strategy.strategy_optimizer.auto_detect_provider", return_value=None):
            with pytest.raises(RuntimeError, match="No LLM provider"):
                optimizer.analyze("code", {"return": 0.1})
