"""
FinClaw Agent Card — serves /.well-known/agent.json per the A2A spec.

Ref: https://google.github.io/A2A/
"""

from __future__ import annotations

from typing import Any

A2A_VERSION = "0.2.0"
FINCLAW_VERSION = "5.13.0"


class FinClawAgentCard:
    """Generate and serve the A2A Agent Card for FinClaw."""

    def __init__(
        self,
        url: str = "http://localhost:8081",
        version: str = FINCLAW_VERSION,
        auth_schemes: list[str] | None = None,
    ):
        self.url = url.rstrip("/")
        self.version = version
        self.auth_schemes = auth_schemes or ["bearer"]

    def generate(self) -> dict[str, Any]:
        """Return the full agent card dictionary."""
        return {
            "name": "FinClaw",
            "description": "AI-native quantitative finance agent — real-time quotes, backtesting, screening, technical & sentiment analysis, and ML predictions across global markets.",
            "url": self.url,
            "version": self.version,
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
            },
            "skills": self._skills(),
            "authentication": {"schemes": self.auth_schemes},
            "provider": {
                "organization": "FinClaw",
                "url": "https://github.com/NeuZhou/finclaw",
            },
            "defaultInputModes": ["text"],
            "defaultOutputModes": ["text"],
        }

    @staticmethod
    def _skills() -> list[dict[str, Any]]:
        return [
            {
                "id": "quote",
                "name": "Get Quote",
                "description": "Get real-time price quotes for stocks, crypto, forex, and commodities across 20+ exchanges.",
                "tags": ["price", "quote", "market-data"],
                "examples": [
                    "What's the price of AAPL?",
                    "Get me a BTC quote",
                    "How much is TSLA trading at?",
                ],
            },
            {
                "id": "backtest",
                "name": "Run Backtest",
                "description": "Backtest trading strategies with full performance metrics, drawdown analysis, and trade logs.",
                "tags": ["backtest", "strategy", "performance"],
                "examples": [
                    "Backtest RSI strategy on BTC from 2023",
                    "Run momentum backtest on AAPL, MSFT, GOOG",
                ],
            },
            {
                "id": "screen",
                "name": "Screen Stocks",
                "description": "Screen and filter stocks by technical indicators, fundamentals, and custom criteria.",
                "tags": ["screener", "filter", "stocks"],
                "examples": [
                    "Find oversold tech stocks",
                    "Screen for stocks with RSI below 30",
                ],
            },
            {
                "id": "analyze",
                "name": "Technical Analysis",
                "description": "Run comprehensive technical analysis with 50+ indicators including RSI, MACD, Bollinger Bands, and more.",
                "tags": ["technical-analysis", "indicators", "charts"],
                "examples": [
                    "Analyze AAPL technicals",
                    "What do the indicators say about NVDA?",
                ],
            },
            {
                "id": "sentiment",
                "name": "Sentiment Analysis",
                "description": "Analyze market sentiment from news, social media, and financial reports.",
                "tags": ["sentiment", "news", "social"],
                "examples": [
                    "What's the sentiment on TSLA?",
                    "Is the market bullish on AI stocks?",
                ],
            },
            {
                "id": "predict",
                "name": "ML Prediction",
                "description": "Machine learning price predictions using ensemble models with confidence intervals.",
                "tags": ["ml", "prediction", "forecast"],
                "examples": [
                    "Predict AAPL price for next week",
                    "ML forecast for Bitcoin",
                ],
            },
        ]

    def to_json(self) -> str:
        """Serialize as JSON string."""
        import json
        return json.dumps(self.generate(), indent=2)
