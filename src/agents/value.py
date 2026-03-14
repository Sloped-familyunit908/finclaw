"""
WhaleTrader - Value Agent (Buffett Style)
Focuses on fundamental analysis, intrinsic value, and margin of safety.
"""

from .base import BaseAgent, Analysis, Signal, MarketData


class ValueAgent(BaseAgent):
    """
    Warren Buffett-inspired value investing agent.
    Focuses on: intrinsic value, margin of safety, competitive moats, earnings quality.
    """

    def __init__(self, ai_client=None):
        super().__init__(
            name="Warren (Value Agent)",
            description="Seeks wonderful companies at fair prices. Focuses on intrinsic value, "
                        "competitive moats, and margin of safety. Patient, long-term oriented.",
            ai_client=ai_client
        )

    async def analyze(self, asset: str, market_data: MarketData, context: dict = None) -> Analysis:
        system_prompt = """You are an AI trading analyst channeling Warren Buffett's investment philosophy.

Your core principles:
1. INTRINSIC VALUE: Calculate what an asset is truly worth, not what the market says
2. MARGIN OF SAFETY: Only buy when price is significantly below intrinsic value (>20% discount)
3. COMPETITIVE MOATS: Look for durable competitive advantages
4. QUALITY EARNINGS: Focus on consistent, growing cash flows
5. LONG-TERM THINKING: Ignore short-term noise, focus on 3-5 year outlook
6. CIRCLE OF COMPETENCE: Only analyze what you understand

For crypto assets, adapt these principles:
- Network effects as moats
- Developer activity as earnings quality
- Tokenomics as capital allocation
- Real usage metrics over speculation

You must respond with a JSON object:
{
    "signal": "strong_buy|buy|hold|sell|strong_sell",
    "confidence": 0.0-1.0,
    "reasoning": "Your detailed analysis",
    "key_factors": ["factor1", "factor2", "factor3"],
    "price_target": null or number,
    "stop_loss": null or number,
    "time_horizon": "short|medium|long"
}"""

        user_prompt = f"""Analyze {asset} from a value investing perspective.

Current Market Data:
- Price: ${market_data.current_price:,.2f}
- 24h Change: {market_data.change_24h:.2%}
- 7d Change: {market_data.change_7d:.2%}
- 30d Change: {market_data.change_30d:.2%}
- 24h Volume: ${market_data.volume_24h:,.0f}
{f'- Market Cap: ${market_data.market_cap:,.0f}' if market_data.market_cap else ''}
{f'- RSI(14): {market_data.rsi_14:.1f}' if market_data.rsi_14 else ''}
{f'- SMA(200): ${market_data.sma_200:,.2f}' if market_data.sma_200 else ''}

Additional Context:
{context.get('news_summary', 'No recent news') if context else 'No additional context'}

Provide your value-based analysis."""

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
                time_horizon=result.get("time_horizon", "long"),
            )
        except Exception as e:
            return Analysis(
                agent_name=self.name,
                asset=asset,
                signal=Signal.HOLD,
                confidence=0.1,
                reasoning=f"Analysis failed: {str(e)}. Defaulting to HOLD.",
                key_factors=["Error in analysis"],
                time_horizon="long",
            )

    async def debate(self, own_analysis: Analysis, other_analyses: list[Analysis]) -> str:
        others_text = "\n\n".join(a.to_debate_statement() for a in other_analyses)

        system_prompt = """You are Warren Buffett in a debate with other investment analysts.
Stay in character. Challenge weak arguments. Support good ones.
Be specific about why you agree or disagree.
Keep it concise but insightful (3-5 sentences)."""

        user_prompt = f"""Your analysis of {own_analysis.asset}:
{own_analysis.to_debate_statement()}

Other analysts' positions:
{others_text}

Respond to their analyses. Where do you agree? Where do you disagree? Why?"""

        return await self._call_ai(system_prompt, user_prompt)
