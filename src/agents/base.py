"""
WhaleTrader - Base Agent Class
All trading agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Signal(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class Analysis:
    """Result of an agent's analysis"""
    agent_name: str
    asset: str
    signal: Signal
    confidence: float  # 0.0 to 1.0
    reasoning: str
    key_factors: list[str] = field(default_factory=list)
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    time_horizon: str = "medium"  # short/medium/long
    timestamp: datetime = field(default_factory=datetime.now)

    def to_debate_statement(self) -> str:
        """Format analysis for the debate arena"""
        signal_emoji = {
            Signal.STRONG_BUY: "🟢🟢",
            Signal.BUY: "🟢",
            Signal.HOLD: "🟡",
            Signal.SELL: "🔴",
            Signal.STRONG_SELL: "🔴🔴",
        }
        emoji = signal_emoji.get(self.signal, "⚪")

        statement = f"""
## {self.agent_name} — {emoji} {self.signal.value.upper()} (Confidence: {self.confidence:.0%})

**Asset**: {self.asset}
**Time Horizon**: {self.time_horizon}
{f'**Price Target**: ${self.price_target:,.2f}' if self.price_target else ''}
{f'**Stop Loss**: ${self.stop_loss:,.2f}' if self.stop_loss else ''}

**Reasoning**: {self.reasoning}

**Key Factors**:
{chr(10).join(f'- {f}' for f in self.key_factors)}
"""
        return statement.strip()


@dataclass
class MarketData:
    """Market data snapshot for analysis"""
    asset: str
    current_price: float
    price_24h_ago: float
    price_7d_ago: float
    price_30d_ago: float
    volume_24h: float
    market_cap: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    # Technical indicators (computed by data pipeline)
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr_14: Optional[float] = None
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def change_24h(self) -> float:
        return (self.current_price - self.price_24h_ago) / self.price_24h_ago

    @property
    def change_7d(self) -> float:
        return (self.current_price - self.price_7d_ago) / self.price_7d_ago

    @property
    def change_30d(self) -> float:
        return (self.current_price - self.price_30d_ago) / self.price_30d_ago


class BaseAgent(ABC):
    """Base class for all trading agents"""

    def __init__(self, name: str, description: str, ai_client=None):
        self.name = name
        self.description = description
        self.ai_client = ai_client  # Claude API client

    @abstractmethod
    async def analyze(self, asset: str, market_data: MarketData, context: dict = None) -> Analysis:
        """
        Analyze an asset and produce a trading signal.
        
        Args:
            asset: Asset symbol (e.g., "BTC", "AAPL")
            market_data: Current market data
            context: Additional context (news, sentiment, etc.)
            
        Returns:
            Analysis object with signal, confidence, and reasoning
        """
        pass

    @abstractmethod
    async def debate(self, own_analysis: Analysis, other_analyses: list[Analysis]) -> str:
        """
        Participate in the debate arena.
        Review other agents' analyses and provide counter-arguments or support.
        
        Args:
            own_analysis: This agent's analysis
            other_analyses: Other agents' analyses
            
        Returns:
            Debate response string
        """
        pass

    async def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Call AI model for analysis. Override for different AI providers."""
        if self.ai_client is None:
            raise ValueError(f"Agent {self.name} has no AI client configured")
        
        # TODO: Implement actual Claude API call
        # For now, return a placeholder
        response = await self.ai_client.chat(
            system=system_prompt,
            message=user_prompt
        )
        return response

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
