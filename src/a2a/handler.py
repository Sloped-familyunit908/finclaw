"""
FinClaw A2A Task Handler — maps A2A tasks to FinClaw operations.

Implements tasks/send, tasks/get, tasks/cancel per the A2A protocol.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class Task:
    """In-memory representation of an A2A task."""

    def __init__(self, task_id: str, message: dict[str, Any]):
        self.id = task_id
        self.state = TaskState.SUBMITTED
        self.message = message  # The original user message
        self.artifacts: list[dict[str, Any]] = []
        self.history: list[dict[str, Any]] = [message]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": {"state": self.state.value, "timestamp": self.updated_at},
            "artifacts": self.artifacts,
            "history": self.history,
        }


# ── Skill routing patterns ───────────────────────────────────────

_SKILL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("quote", re.compile(r"\b(price|quote|trading at|how much|current value)\b", re.I)),
    ("backtest", re.compile(r"\b(backtest|back-test|test strategy)\b", re.I)),
    ("screen", re.compile(r"\b(screen|filter|find stocks|scan|oversold|overbought)\b", re.I)),
    ("analyze", re.compile(r"\b(analy[sz]e|technical|indicators?|rsi|macd|bollinger)\b", re.I)),
    ("sentiment", re.compile(r"\b(sentiment|news|bull|bear|social|opinion)\b", re.I)),
    ("predict", re.compile(r"\b(predict|forecast|ml|machine learning|next week|next month)\b", re.I)),
]


def route_skill(text: str) -> str | None:
    """Determine which FinClaw skill best matches the user text."""
    for skill_id, pattern in _SKILL_PATTERNS:
        if pattern.search(text):
            return skill_id
    return None


def _extract_symbols(text: str) -> list[str]:
    """Extract ticker-like symbols from text."""
    # Match uppercase 1-5 letter words that look like tickers
    candidates = re.findall(r'\b([A-Z]{1,5})\b', text)
    # Filter out common English words
    stopwords = {
        "I", "A", "THE", "AND", "OR", "FOR", "IN", "ON", "AT", "TO",
        "IS", "IT", "OF", "BY", "AS", "AN", "BE", "DO", "IF", "MY",
        "SO", "UP", "NO", "HE", "WE", "AM", "GET", "RUN", "SET",
        "ALL", "HAS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD",
        "SEE", "WAY", "WHO", "DID", "GOT", "HIM", "HIS", "LET",
        "SAY", "SHE", "TOO", "USE", "HER", "WAS", "ONE", "OUR",
        "OUT", "DAY", "HAD", "NOT", "BUT", "WHAT", "SOME", "CAN",
        "FROM", "THIS", "THAT", "WITH", "HAVE", "WILL", "YOUR",
        "FIND", "MUCH", "NEXT", "WEEK", "SHOW",
    }
    # Also allow crypto pairs like BTC, ETH
    return [c for c in candidates if c not in stopwords]


class A2ATaskHandler:
    """
    Handle A2A task lifecycle.

    Maintains an in-memory task store and dispatches to FinClaw operations.
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._skill_handlers: dict[str, Callable] = {
            "quote": self._handle_quote,
            "backtest": self._handle_backtest,
            "screen": self._handle_screen,
            "analyze": self._handle_analyze,
            "sentiment": self._handle_sentiment,
            "predict": self._handle_predict,
        }

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def handle_task_send(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Process tasks/send — create a task from a message and execute it.

        Args:
            request: A2A tasks/send params with 'id' (optional) and 'message'.

        Returns:
            Task object dict with status and artifacts.
        """
        task_id = request.get("id") or str(uuid.uuid4())
        message = request.get("message", {})

        task = Task(task_id, message)
        self._tasks[task_id] = task

        # Extract text from message parts
        text = self._extract_text(message)
        if not text:
            task.state = TaskState.FAILED
            task.updated_at = datetime.now(timezone.utc).isoformat()
            task.artifacts = [{"parts": [{"type": "text", "text": "No text content in message."}]}]
            return task.to_dict()

        # Route to skill
        skill_id = route_skill(text)
        if skill_id is None:
            task.state = TaskState.FAILED
            task.updated_at = datetime.now(timezone.utc).isoformat()
            task.artifacts = [
                {"parts": [{"type": "text", "text": f"Could not determine which skill to use for: {text}"}]}
            ]
            return task.to_dict()

        # Execute skill handler
        task.state = TaskState.WORKING
        task.updated_at = datetime.now(timezone.utc).isoformat()

        try:
            handler = self._skill_handlers[skill_id]
            result_text = handler(text)
            task.state = TaskState.COMPLETED
            task.artifacts = [{"parts": [{"type": "text", "text": result_text}]}]
        except Exception as e:
            task.state = TaskState.FAILED
            task.artifacts = [{"parts": [{"type": "text", "text": f"Error: {e}"}]}]

        task.updated_at = datetime.now(timezone.utc).isoformat()
        return task.to_dict()

    def handle_task_get(self, task_id: str) -> dict[str, Any] | None:
        """Retrieve a task by ID. Returns None if not found."""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def handle_task_cancel(self, task_id: str) -> dict[str, Any] | None:
        """Cancel a task. Returns None if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED):
            return task.to_dict()  # Already terminal
        task.state = TaskState.CANCELED
        task.updated_at = datetime.now(timezone.utc).isoformat()
        return task.to_dict()

    # ── Skill handlers ────────────────────────────────────────────

    @staticmethod
    def _extract_text(message: dict) -> str:
        """Extract plain text from A2A message parts."""
        parts = message.get("parts", [])
        texts = []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part["text"])
            elif isinstance(part, str):
                texts.append(part)
        # Fallback: if message has a direct 'text' key
        if not texts and "text" in message:
            texts.append(message["text"])
        return " ".join(texts).strip()

    def _handle_quote(self, text: str) -> str:
        symbols = _extract_symbols(text)
        if not symbols:
            return "Please specify a ticker symbol (e.g., AAPL, BTC, TSLA)."
        results = []
        for sym in symbols[:5]:  # Limit to 5
            results.append(f"Quote for {sym}: [routed to FinClaw quote engine]")
        return "\n".join(results)

    def _handle_backtest(self, text: str) -> str:
        symbols = _extract_symbols(text)
        sym_str = ", ".join(symbols[:3]) if symbols else "SPY"
        return f"Backtest initiated for [{sym_str}]: [routed to FinClaw backtest engine]"

    def _handle_screen(self, text: str) -> str:
        return f"Stock screening: [routed to FinClaw screener] — query: {text[:100]}"

    def _handle_analyze(self, text: str) -> str:
        symbols = _extract_symbols(text)
        sym = symbols[0] if symbols else "SPY"
        return f"Technical analysis for {sym}: [routed to FinClaw TA engine]"

    def _handle_sentiment(self, text: str) -> str:
        symbols = _extract_symbols(text)
        sym = symbols[0] if symbols else "market"
        return f"Sentiment analysis for {sym}: [routed to FinClaw sentiment engine]"

    def _handle_predict(self, text: str) -> str:
        symbols = _extract_symbols(text)
        sym = symbols[0] if symbols else "SPY"
        return f"ML prediction for {sym}: [routed to FinClaw ML engine]"
