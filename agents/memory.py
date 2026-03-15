"""
FinClaw - Agent Memory & Reputation System
2027 Agentic AI核心方向：Agent有记忆，知道自己过去哪些判断对了。

Inspired by:
- ELO rating system (chess)
- Bayesian updating (statistics)
- RD-Agent(Q) feedback loop (NeurIPS 2025)
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path


@dataclass
class PredictionRecord:
    """A single historical prediction"""
    timestamp: datetime
    asset: str
    signal: str
    confidence: float
    price_at_prediction: float
    price_after_24h: Optional[float] = None
    price_after_7d: Optional[float] = None
    was_correct: Optional[bool] = None
    pnl_pct: Optional[float] = None


@dataclass
class AgentMemory:
    """
    Persistent memory for a trading agent.
    Tracks accuracy, specialization, and evolving reputation.
    """
    agent_name: str
    
    # Performance tracking
    predictions: list[PredictionRecord] = field(default_factory=list)
    total_predictions: int = 0
    correct_predictions: int = 0
    
    # ELO-style reputation (starts at 1200, like chess)
    elo_rating: float = 1200.0
    
    # Specialization scores: which assets/conditions this agent excels at
    asset_accuracy: dict[str, list[bool]] = field(default_factory=dict)
    bullish_accuracy: float = 0.5  # accuracy on buy signals
    bearish_accuracy: float = 0.5  # accuracy on sell signals
    
    # Debate performance
    times_dissented_and_was_right: int = 0
    times_dissented_and_was_wrong: int = 0
    debate_win_rate: float = 0.5
    
    # Meta-learning: what conditions does this agent perform best in?
    best_conditions: list[str] = field(default_factory=list)
    worst_conditions: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.total_predictions == 0:
            return 0.5  # prior
        return self.correct_predictions / self.total_predictions

    @property
    def debate_weight(self) -> float:
        """Weight this agent's opinion in debates based on reputation.
        Higher ELO → more influence in consensus."""
        # Sigmoid mapping: 1200 ELO → 1.0x, 1400 → 1.5x, 1000 → 0.67x
        return 1.0 / (1.0 + math.exp(-(self.elo_rating - 1200) / 100))

    def record_prediction(self, asset: str, signal: str, 
                          confidence: float, price: float):
        """Record a new prediction"""
        record = PredictionRecord(
            timestamp=datetime.now(),
            asset=asset,
            signal=signal,
            confidence=confidence,
            price_at_prediction=price,
        )
        self.predictions.append(record)
        self.total_predictions += 1

    def resolve_prediction(self, index: int, actual_price: float):
        """Resolve a past prediction with actual outcome"""
        if index >= len(self.predictions):
            return

        pred = self.predictions[index]
        if pred.was_correct is not None:
            return  # Already resolved

        pnl_pct = (actual_price - pred.price_at_prediction) / pred.price_at_prediction
        pred.price_after_24h = actual_price
        pred.pnl_pct = pnl_pct

        # Determine if prediction was correct
        if pred.signal in ("buy", "strong_buy"):
            pred.was_correct = pnl_pct > 0.005  # >0.5% gain = correct
        elif pred.signal in ("sell", "strong_sell"):
            pred.was_correct = pnl_pct < -0.005
        else:  # hold
            pred.was_correct = abs(pnl_pct) < 0.02  # <2% move = correct

        if pred.was_correct:
            self.correct_predictions += 1

        # Update ELO
        self._update_elo(pred.was_correct, pred.confidence)
        
        # Update asset specialization
        if pred.asset not in self.asset_accuracy:
            self.asset_accuracy[pred.asset] = []
        self.asset_accuracy[pred.asset].append(pred.was_correct)

        # Update directional accuracy
        if pred.signal in ("buy", "strong_buy"):
            self._update_running_avg("bullish_accuracy", pred.was_correct)
        elif pred.signal in ("sell", "strong_sell"):
            self._update_running_avg("bearish_accuracy", pred.was_correct)

    def _update_elo(self, won: bool, confidence: float):
        """Update ELO rating. Higher confidence wrong predictions lose more."""
        K = 32  # Standard K-factor
        expected = 1.0 / (1.0 + math.pow(10, (1200 - self.elo_rating) / 400))
        actual = 1.0 if won else 0.0
        
        # Confidence multiplier: being confidently wrong hurts more
        if not won and confidence > 0.8:
            K *= 1.5  # Extra penalty for overconfidence
        elif won and confidence > 0.8:
            K *= 1.2  # Small bonus for confident correctness

        self.elo_rating += K * (actual - expected)
        self.elo_rating = max(800, min(2000, self.elo_rating))  # Clamp

    def _update_running_avg(self, attr: str, value: bool):
        """Exponential moving average update"""
        alpha = 0.1
        current = getattr(self, attr)
        setattr(self, attr, current * (1 - alpha) + (1.0 if value else 0.0) * alpha)

    def get_asset_accuracy(self, asset: str) -> float:
        """Get accuracy for a specific asset"""
        history = self.asset_accuracy.get(asset, [])
        if not history:
            return 0.5  # prior
        return sum(history) / len(history)

    def get_reputation_card(self) -> str:
        """Human-readable reputation summary"""
        stars = "⭐" * min(5, max(1, int(self.elo_rating / 250)))
        return (
            f"  {self.agent_name} — ELO: {self.elo_rating:.0f} {stars}\n"
            f"  Accuracy: {self.accuracy:.1%} ({self.correct_predictions}/{self.total_predictions})\n"
            f"  Debate Weight: {self.debate_weight:.2f}x\n"
            f"  Bull Accuracy: {self.bullish_accuracy:.1%} | Bear Accuracy: {self.bearish_accuracy:.1%}\n"
        )

    def save(self, filepath: str):
        """Persist memory to disk"""
        data = {
            "agent_name": self.agent_name,
            "elo_rating": self.elo_rating,
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "bullish_accuracy": self.bullish_accuracy,
            "bearish_accuracy": self.bearish_accuracy,
            "debate_win_rate": self.debate_win_rate,
            "times_dissented_right": self.times_dissented_and_was_right,
            "times_dissented_wrong": self.times_dissented_and_was_wrong,
            "asset_accuracy": {k: v for k, v in self.asset_accuracy.items()},
            "predictions": [
                {
                    "timestamp": p.timestamp.isoformat(),
                    "asset": p.asset,
                    "signal": p.signal,
                    "confidence": p.confidence,
                    "price_at_prediction": p.price_at_prediction,
                    "was_correct": p.was_correct,
                    "pnl_pct": p.pnl_pct,
                }
                for p in self.predictions[-100:]  # Keep last 100
            ],
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "AgentMemory":
        """Load memory from disk"""
        try:
            with open(filepath) as f:
                data = json.load(f)
        except FileNotFoundError:
            return cls(agent_name="unknown")

        memory = cls(agent_name=data["agent_name"])
        memory.elo_rating = data.get("elo_rating", 1200.0)
        memory.total_predictions = data.get("total_predictions", 0)
        memory.correct_predictions = data.get("correct_predictions", 0)
        memory.bullish_accuracy = data.get("bullish_accuracy", 0.5)
        memory.bearish_accuracy = data.get("bearish_accuracy", 0.5)
        memory.debate_win_rate = data.get("debate_win_rate", 0.5)
        memory.asset_accuracy = data.get("asset_accuracy", {})
        return memory


class MemoryManager:
    """Manages memories for all agents"""
    
    def __init__(self, storage_dir: str = ".whale/memories"):
        self.storage_dir = Path(storage_dir)
        self.memories: dict[str, AgentMemory] = {}

    def get_memory(self, agent_name: str) -> AgentMemory:
        if agent_name not in self.memories:
            filepath = self.storage_dir / f"{agent_name.lower()}.json"
            if filepath.exists():
                self.memories[agent_name] = AgentMemory.load(str(filepath))
            else:
                self.memories[agent_name] = AgentMemory(agent_name=agent_name)
        return self.memories[agent_name]

    def save_all(self):
        for name, memory in self.memories.items():
            filepath = self.storage_dir / f"{name.lower()}.json"
            memory.save(str(filepath))

    def get_leaderboard(self) -> str:
        """Get agent reputation leaderboard"""
        sorted_agents = sorted(
            self.memories.values(),
            key=lambda m: m.elo_rating,
            reverse=True,
        )
        lines = ["  AGENT REPUTATION LEADERBOARD", "  " + "="*50]
        for i, m in enumerate(sorted_agents):
            rank = f"#{i+1}"
            lines.append(f"  {rank} {m.get_reputation_card()}")
        return "\n".join(lines)
