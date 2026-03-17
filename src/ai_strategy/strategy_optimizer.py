"""
AI Strategy Optimizer
=====================
Analyze backtest results + suggest parameter improvements using LLM + grid search.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from typing import Any, Callable, Dict, List, Optional

from src.llm.registry import auto_detect_provider, get_provider
from src.llm.base import LLMProvider
from src.ai_strategy.prompt_templates import build_optimization_prompt

logger = logging.getLogger("finclaw.ai_strategy")


class StrategyOptimizer:
    """Combine AI heuristics with grid search for strategy optimization."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        provider_name: Optional[str] = None,
    ):
        self._provider = provider
        self._provider_name = provider_name

    def _get_provider(self) -> LLMProvider:
        if self._provider:
            return self._provider
        if self._provider_name:
            return get_provider(self._provider_name)
        provider = auto_detect_provider()
        if provider is None:
            raise RuntimeError("No LLM provider available.")
        return provider

    async def analyze_async(
        self,
        strategy_code: str,
        backtest_results: dict,
    ) -> dict:
        """
        AI analysis of strategy + backtest results.

        Returns:
            {"analysis": str, "suggestions": list, "code_improvements": str, "risk_assessment": str}
        """
        provider = self._get_provider()
        prompt = build_optimization_prompt(strategy_code, backtest_results)
        messages = [
            {"role": "system", "content": "You are a quantitative strategy analyst. Respond with JSON only."},
            {"role": "user", "content": prompt},
        ]
        result = await provider.chat_json(messages, temperature=0.3)
        return result

    def analyze(self, strategy_code: str, backtest_results: dict) -> dict:
        """Sync wrapper."""
        return asyncio.run(self.analyze_async(strategy_code, backtest_results))

    def grid_search(
        self,
        evaluate_fn: Callable[[Dict[str, Any]], float],
        param_grid: Dict[str, List[Any]],
        maximize: bool = True,
    ) -> dict:
        """
        Exhaustive grid search over parameter combinations.

        Args:
            evaluate_fn: Takes params dict, returns metric (e.g. Sharpe ratio).
            param_grid: {"param_name": [val1, val2, ...], ...}
            maximize: If True, find max; if False, find min.

        Returns:
            {"best_params": dict, "best_score": float, "all_results": list}
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        all_results = []
        best_score = float("-inf") if maximize else float("inf")
        best_params: Dict[str, Any] = {}

        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            try:
                score = evaluate_fn(params)
                all_results.append({"params": params, "score": score})
                if (maximize and score > best_score) or (not maximize and score < best_score):
                    best_score = score
                    best_params = params.copy()
            except Exception as e:
                logger.warning("Grid search error for %s: %s", params, e)
                all_results.append({"params": params, "score": None, "error": str(e)})

        return {
            "best_params": best_params,
            "best_score": best_score,
            "all_results": all_results,
        }

    async def smart_optimize_async(
        self,
        strategy_code: str,
        backtest_results: dict,
        evaluate_fn: Optional[Callable] = None,
        param_grid: Optional[Dict[str, List]] = None,
    ) -> dict:
        """
        Combined AI + grid search optimization.

        1. AI analyzes results and suggests parameter changes
        2. If evaluate_fn + param_grid provided, runs grid search too
        3. Returns merged recommendations
        """
        ai_result = await self.analyze_async(strategy_code, backtest_results)

        grid_result = None
        if evaluate_fn and param_grid:
            grid_result = self.grid_search(evaluate_fn, param_grid)

        return {
            "ai_analysis": ai_result,
            "grid_search": grid_result,
        }

    def smart_optimize(self, *args, **kwargs) -> dict:
        """Sync wrapper."""
        return asyncio.run(self.smart_optimize_async(*args, **kwargs))
