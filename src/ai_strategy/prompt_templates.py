"""
Prompt Templates for AI Strategy Generation
============================================
Few-shot examples, market-specific prompts, and output formatting.
"""

from __future__ import annotations

# ── Few-shot example: a real StrategyPlugin ──────────────────────

STRATEGY_PLUGIN_EXAMPLE = '''
import pandas as pd
from src.plugin_system.plugin_types import StrategyPlugin


class RSIMACDStrategy(StrategyPlugin):
    """Buy when RSI < 30 and MACD crosses above signal; sell when RSI > 70."""

    name = "rsi_macd_crossover"
    version = "1.0.0"
    description = "RSI oversold + MACD golden cross entry, RSI overbought exit"
    author = "finclaw-ai"
    risk_level = "medium"
    markets = ["us_stock"]

    def __init__(self, rsi_period: int = 14, rsi_oversold: float = 30,
                 rsi_overbought: float = 70, macd_fast: int = 12,
                 macd_slow: int = 26, macd_signal: int = 9,
                 stop_loss_pct: float = 0.05):
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.stop_loss_pct = stop_loss_pct

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["Close"]
        signals = pd.Series(0, index=data.index)

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, 1e-10)
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema_fast = close.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        macd_cross_up = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))

        # Entry: RSI oversold + MACD golden cross
        signals[macd_cross_up & (rsi < self.rsi_oversold)] = 1

        # Exit: RSI overbought
        signals[rsi > self.rsi_overbought] = -1

        return signals

    def get_parameters(self) -> dict:
        return {
            "rsi_period": self.rsi_period,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "macd_fast": self.macd_fast,
            "macd_slow": self.macd_slow,
            "macd_signal": self.macd_signal,
            "stop_loss_pct": self.stop_loss_pct,
        }

    def backtest_config(self) -> dict:
        return {
            "initial_capital": 100000,
            "commission": 0.001,
            "slippage": 0.0005,
            "stop_loss": self.stop_loss_pct,
        }
'''

# ── Market-specific context ──────────────────────────────────────

MARKET_CONTEXT = {
    "us_stock": (
        "US equities (NYSE/NASDAQ). Data columns: Open, High, Low, Close, Volume. "
        "Trading hours 9:30-16:00 ET. Typical indicators: RSI, MACD, SMA, EMA, Bollinger Bands, ATR, VWAP."
    ),
    "crypto": (
        "Cryptocurrency markets (24/7). Data columns: Open, High, Low, Close, Volume. "
        "High volatility — wider stop losses recommended. "
        "Typical indicators: RSI, MACD, Bollinger Bands, OBV, funding rate awareness."
    ),
    "cn_stock": (
        "A-share market (China). Data columns: Open, High, Low, Close, Volume. "
        "T+1 settlement — cannot sell on buying day. ±10% daily limit (±20% for ChiNext). "
        "Typical indicators: RSI, MACD, KDJ, turnover rate."
    ),
}

RISK_PROFILES = {
    "low": "Conservative: tight stop losses (2-3%), prefer trend-following, avoid leverage.",
    "medium": "Balanced: moderate stop losses (5%), mix of trend and mean reversion.",
    "high": "Aggressive: wider stop losses (8-10%), momentum plays, higher position sizing.",
}


def build_system_prompt(market: str = "us_stock", risk: str = "medium") -> str:
    """Build the system prompt for strategy generation."""
    market_ctx = MARKET_CONTEXT.get(market, MARKET_CONTEXT["us_stock"])
    risk_ctx = RISK_PROFILES.get(risk, RISK_PROFILES["medium"])

    return f"""You are FinClaw Strategy Architect, an expert quantitative strategy developer.

## Your Task
Generate a complete Python StrategyPlugin class that implements a trading strategy
described by the user in natural language.

## Output Format
Output ONLY valid Python code. No markdown fences, no explanations before or after.
The code must:
1. Import pandas as pd and StrategyPlugin from src.plugin_system.plugin_types
2. Define exactly ONE class that inherits from StrategyPlugin
3. Set all required class attributes: name, version, description, author, risk_level, markets
4. Implement generate_signals(self, data: pd.DataFrame) -> pd.Series (1=buy, -1=sell, 0=hold)
5. Implement get_parameters(self) -> dict
6. Optionally override backtest_config(self) -> dict
7. All indicator calculations must be inline (no external TA library imports)
8. Include stop-loss logic if the user mentions it

## Market Context
{market_ctx}

## Risk Profile
{risk_ctx}

## Example
Here is a complete example of a well-formed strategy:
{STRATEGY_PLUGIN_EXAMPLE}

Generate a strategy following this exact pattern."""


def build_user_prompt(description: str) -> str:
    """Build the user message for strategy generation."""
    return f"Create a FinClaw StrategyPlugin for: {description}"


def build_optimization_prompt(strategy_code: str, backtest_results: dict) -> str:
    """Build prompt for strategy optimization analysis."""
    return f"""Analyze this trading strategy and its backtest results, then suggest improvements.

## Strategy Code
```python
{strategy_code}
```

## Backtest Results
{_format_results(backtest_results)}

## Your Task
Respond in JSON with this structure:
{{
  "analysis": "brief analysis of strengths and weaknesses",
  "suggestions": [
    {{"parameter": "param_name", "current": current_val, "suggested": new_val, "reason": "why"}},
    ...
  ],
  "code_improvements": "brief description of any code-level improvements",
  "risk_assessment": "low|medium|high and why"
}}
"""


def _format_results(results: dict) -> str:
    lines = []
    for k, v in results.items():
        if isinstance(v, float):
            lines.append(f"- {k}: {v:.4f}")
        else:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def build_copilot_system_prompt() -> str:
    """System prompt for the FinClaw Copilot chat mode."""
    return """You are FinClaw Copilot, an AI financial analysis assistant.

You help users with:
1. Analyzing stock/crypto trends — provide technical analysis summaries
2. Creating trading strategies — guide users step-by-step, then generate StrategyPlugin code
3. Comparing backtest results — create clear comparison tables
4. Explaining financial concepts — in plain language

When generating strategy code, follow the StrategyPlugin format exactly.
When analyzing data, be specific with numbers and actionable insights.
Keep responses concise but informative."""
