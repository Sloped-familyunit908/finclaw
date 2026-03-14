"""WhaleTrader Agents Package"""

from .registry import get_agent, list_agents, BUILTIN_AGENTS
from .debate_arena import DebateArena, DebateResult, DebateStatement, DebatePhase
from .backtester import Backtester, BacktestResult, compare_strategies
from .ai_client import create_client, ClaudeClient, OpenAIClient, OllamaClient, AzureOpenAIClient

__all__ = [
    "get_agent", "list_agents", "BUILTIN_AGENTS",
    "DebateArena", "DebateResult", "DebateStatement", "DebatePhase",
    "Backtester", "BacktestResult", "compare_strategies",
    "create_client", "ClaudeClient", "OpenAIClient", "OllamaClient", "AzureOpenAIClient",
]
