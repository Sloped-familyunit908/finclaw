"""
FinClaw - Momentum Agent
Technical analysis and trend following.
"""

from .base import BaseAgent, Analysis, Signal, MarketData


class MomentumAgent(BaseAgent):
    """
    Technical/Momentum trading agent.
    Focuses on: price trends, technical indicators, volume analysis, chart patterns.
    """

    def __init__(self, ai_client=None):
        super().__init__(
            name="Momentum Agent",
            description="Pure technical analyst. Follows trends, reads charts, respects momentum. "
                        "Believes price action tells the truth before fundamentals do.",
            ai_client=ai_client
        )

    async def analyze(self, asset: str, market_data: MarketData, context: dict = None) -> Analysis:
        system_prompt = """You are a quantitative technical analyst. You analyze price action, 
momentum indicators, and volume patterns to generate trading signals.

Your toolkit:
1. RSI (Relative Strength Index) — Overbought >70, Oversold <30
2. MACD — Trend direction and momentum shifts
3. Moving Averages — SMA 20/50/200 for trend identification
4. Bollinger Bands — Volatility and mean reversion
5. Volume Analysis — Confirmation of price moves
6. ATR — Volatility measurement for position sizing

Rules:
- ALWAYS respect the trend. "Trend is your friend until the bend."
- Volume confirms price. Low volume moves are suspect.
- Multiple timeframe agreement = higher confidence.
- RSI divergence often precedes trend reversals.

Respond with JSON:
{
    "signal": "strong_buy|buy|hold|sell|strong_sell",
    "confidence": 0.0-1.0,
    "reasoning": "Your technical analysis",
    "key_factors": ["factor1", "factor2", "factor3"],
    "price_target": null or number,
    "stop_loss": null or number,
    "time_horizon": "short|medium|long"
}"""

        indicators = []
        if market_data.rsi_14 is not None:
            indicators.append(f"RSI(14): {market_data.rsi_14:.1f}")
        if market_data.macd is not None:
            indicators.append(f"MACD: {market_data.macd:.4f}")
        if market_data.macd_signal is not None:
            indicators.append(f"MACD Signal: {market_data.macd_signal:.4f}")
        if market_data.sma_20 is not None:
            indicators.append(f"SMA(20): ${market_data.sma_20:,.2f}")
        if market_data.sma_50 is not None:
            indicators.append(f"SMA(50): ${market_data.sma_50:,.2f}")
        if market_data.sma_200 is not None:
            indicators.append(f"SMA(200): ${market_data.sma_200:,.2f}")
        if market_data.bollinger_upper is not None:
            indicators.append(f"BB Upper: ${market_data.bollinger_upper:,.2f}")
        if market_data.bollinger_lower is not None:
            indicators.append(f"BB Lower: ${market_data.bollinger_lower:,.2f}")
        if market_data.atr_14 is not None:
            indicators.append(f"ATR(14): ${market_data.atr_14:,.2f}")

        user_prompt = f"""Technical analysis for {asset}.

Price Data:
- Current Price: ${market_data.current_price:,.2f}
- 24h High/Low: ${market_data.high_24h:,.2f} / ${market_data.low_24h:,.2f}
- 24h Change: {market_data.change_24h:.2%}
- 7d Change: {market_data.change_7d:.2%}
- 30d Change: {market_data.change_30d:.2%}
- 24h Volume: ${market_data.volume_24h:,.0f}

Technical Indicators:
{chr(10).join(f'- {ind}' for ind in indicators) if indicators else '- No indicators available'}

Trend Context:
- Price vs SMA20: {'Above ✅' if market_data.sma_20 and market_data.current_price > market_data.sma_20 else 'Below ❌' if market_data.sma_20 else 'N/A'}
- Price vs SMA200: {'Above ✅' if market_data.sma_200 and market_data.current_price > market_data.sma_200 else 'Below ❌' if market_data.sma_200 else 'N/A'}

Generate your technical signal."""

        try:
            response = await self._call_ai(system_prompt, user_prompt)
            import json
            result = json.loads(response)

            return Analysis(
                agent_name=self.name,
                asset=asset,
                signal=Signal(result["signal"]),
                confidence=result["confidence"],
                reasoning=result["reasoning"],
                key_factors=result.get("key_factors", []),
                price_target=result.get("price_target"),
                stop_loss=result.get("stop_loss"),
                time_horizon=result.get("time_horizon", "short"),
            )
        except Exception as e:
            return Analysis(
                agent_name=self.name,
                asset=asset,
                signal=Signal.HOLD,
                confidence=0.1,
                reasoning=f"Analysis failed: {str(e)}. Defaulting to HOLD.",
                key_factors=["Error in analysis"],
                time_horizon="short",
            )

    async def debate(self, own_analysis: Analysis, other_analyses: list[Analysis]) -> str:
        others_text = "\n\n".join(a.to_debate_statement() for a in other_analyses)

        system_prompt = """You are a technical analyst in a debate with fundamental and macro analysts.
You believe price action is the ultimate truth. Challenge analyses that ignore what the chart is saying.
Be data-driven and specific. Reference actual indicator values."""

        user_prompt = f"""Your analysis of {own_analysis.asset}:
{own_analysis.to_debate_statement()}

Other analysts' positions:
{others_text}

Respond to their analyses from a technical perspective."""

        return await self._call_ai(system_prompt, user_prompt)
