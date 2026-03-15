"""
FinClaw - Debate Arena
The core innovation: AI agents debate before any trade decision.

Based on:
- "Improving Factuality and Reasoning through Multiagent Debate" (Du et al., 2023)
- "R&D-Agent-Quant" (Li et al., NeurIPS 2025)

Protocol: Adversarial Debate Protocol for Trading (ADP-T)
1. Independent Analysis Phase — agents analyze without seeing others
2. Position Statement — each agent declares their signal + reasoning
3. Challenge Phase — agents critique each other's logic
4. Defense Phase — agents defend or update their positions
5. Consensus — moderator synthesizes final decision
"""

import json
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class DebatePhase(Enum):
    ANALYSIS = "analysis"
    POSITION = "position"
    CHALLENGE = "challenge"
    DEFENSE = "defense"
    CONSENSUS = "consensus"


@dataclass
class DebateStatement:
    """A single statement in the debate"""
    agent_name: str
    agent_role: str  # e.g., "Value Investor", "Technical Analyst"
    phase: DebatePhase
    content: str
    signal: str  # buy/sell/hold
    confidence: float
    target_agent: Optional[str] = None  # who they're responding to
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent_name,
            "role": self.agent_role,
            "phase": self.phase.value,
            "content": self.content,
            "signal": self.signal,
            "confidence": self.confidence,
            "target": self.target_agent,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class DebateResult:
    """Final result of a debate session"""
    asset: str
    final_signal: str
    final_confidence: float
    consensus_reasoning: str
    rounds: list[list[DebateStatement]]
    participating_agents: list[str]
    dissenting_agents: list[str]  # agents who disagreed with consensus
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "signal": self.final_signal,
            "confidence": self.final_confidence,
            "reasoning": self.consensus_reasoning,
            "participants": self.participating_agents,
            "dissenters": self.dissenting_agents,
            "rounds": [[s.to_dict() for s in r] for r in self.rounds],
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class DebateArena:
    """
    The Debate Arena where AI agents argue about trading decisions.
    
    This is FinClaw's killer feature — no other trading platform has this.
    Users can watch agents debate in real-time through the Dashboard.
    """

    def __init__(self, ai_client=None, max_rounds: int = 3,
                 consensus_threshold: float = 0.7):
        self.ai_client = ai_client
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.debate_history: list[DebateResult] = []

    async def run_debate(self, asset: str, agents: list,
                         market_data: dict, context: dict = None,
                         on_statement=None) -> DebateResult:
        """
        Run a full debate session.
        
        Args:
            asset: Asset being analyzed (e.g., "BTC")
            agents: List of AI agent instances
            market_data: Current market data dict
            context: Additional context (news, sentiment, etc.)
            on_statement: Async callback for real-time UI updates
            
        Returns:
            DebateResult with consensus decision
        """
        start_time = datetime.now()
        all_rounds = []

        # ─── Phase 1: Independent Analysis ────────────────────
        analysis_statements = await self._independent_analysis(
            asset, agents, market_data, context
        )
        all_rounds.append(analysis_statements)

        if on_statement:
            for stmt in analysis_statements:
                await on_statement(stmt)

        # ─── Phase 2-3: Challenge & Defense Rounds ────────────
        prev_statements = analysis_statements
        for round_num in range(self.max_rounds):
            # Challenge phase
            challenges = await self._challenge_phase(
                asset, agents, prev_statements
            )
            all_rounds.append(challenges)
            
            if on_statement:
                for stmt in challenges:
                    await on_statement(stmt)

            # Check if consensus already reached
            if self._check_consensus(challenges):
                break

            prev_statements = challenges

        # ─── Phase 4: Consensus ───────────────────────────────
        all_statements = [s for round_stmts in all_rounds for s in round_stmts]
        consensus = await self._build_consensus(asset, all_statements)
        all_rounds.append([consensus])
        
        if on_statement:
            await on_statement(consensus)

        # Build result
        duration = (datetime.now() - start_time).total_seconds() * 1000

        # Find dissenters
        final_signal = consensus.signal
        dissenters = [
            s.agent_name for s in analysis_statements
            if s.signal != final_signal and s.confidence > 0.5
        ]

        result = DebateResult(
            asset=asset,
            final_signal=final_signal,
            final_confidence=consensus.confidence,
            consensus_reasoning=consensus.content,
            rounds=all_rounds,
            participating_agents=[a.name for a in agents],
            dissenting_agents=dissenters,
            duration_ms=duration,
        )

        self.debate_history.append(result)
        return result

    async def _independent_analysis(self, asset, agents, market_data, context):
        """Phase 1: Each agent analyzes independently"""
        statements = []

        # Run all agents in parallel for speed
        tasks = []
        for agent in agents:
            tasks.append(self._get_agent_analysis(agent, asset, market_data, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                statements.append(DebateStatement(
                    agent_name=agent.name,
                    agent_role=agent.role,
                    phase=DebatePhase.POSITION,
                    content=f"Analysis failed: {str(result)}",
                    signal="hold",
                    confidence=0.1,
                ))
            else:
                statements.append(result)

        return statements

    async def _get_agent_analysis(self, agent, asset, market_data, context):
        """Get a single agent's analysis"""
        if self.ai_client is None:
            # Fallback: use rule-based analysis
            return self._rule_based_analysis(agent, asset, market_data)

        prompt = f"""You are {agent.name}, a {agent.role}.

Analyze {asset} and provide your trading recommendation.

Market Data:
{json.dumps(market_data, indent=2, default=str)}

{f"Additional Context: {json.dumps(context, indent=2)}" if context else ""}

Respond in JSON format:
{{
    "signal": "strong_buy|buy|hold|sell|strong_sell",
    "confidence": 0.0-1.0,
    "reasoning": "Your detailed analysis (2-3 sentences)",
    "key_factors": ["factor1", "factor2", "factor3"]
}}"""

        response = await self.ai_client.chat(
            system=agent.system_prompt,
            message=prompt,
        )

        data = json.loads(response)
        return DebateStatement(
            agent_name=agent.name,
            agent_role=agent.role,
            phase=DebatePhase.POSITION,
            content=data["reasoning"],
            signal=data["signal"],
            confidence=data["confidence"],
        )

    async def _challenge_phase(self, asset, agents, prev_statements):
        """Challenge phase: agents critique each other"""
        challenges = []

        for agent in agents:
            # Each agent sees others' statements and responds
            others = [s for s in prev_statements if s.agent_name != agent.name]

            if not others:
                continue

            if self.ai_client is None:
                # Rule-based: maintain position
                own_stmt = next(
                    (s for s in prev_statements if s.agent_name == agent.name),
                    None
                )
                if own_stmt:
                    challenges.append(DebateStatement(
                        agent_name=agent.name,
                        agent_role=agent.role,
                        phase=DebatePhase.CHALLENGE,
                        content=f"I maintain my {own_stmt.signal} position. "
                                f"While {others[0].agent_name} argues for {others[0].signal}, "
                                f"my analysis stands.",
                        signal=own_stmt.signal,
                        confidence=own_stmt.confidence,
                        target_agent=others[0].agent_name,
                    ))
                continue

            others_text = "\n".join(
                f"- {s.agent_name} ({s.agent_role}): {s.signal.upper()} "
                f"(confidence: {s.confidence:.0%}) — {s.content}"
                for s in others
            )

            prompt = f"""You are {agent.name} in a trading debate about {asset}.

Other analysts' positions:
{others_text}

Challenge the weakest argument. Be specific.
Also state whether you update your own position.

Respond in JSON:
{{
    "target_agent": "name of agent you're challenging",
    "challenge": "Your specific critique (2-3 sentences)",
    "signal": "your updated signal",
    "confidence": 0.0-1.0
}}"""

            response = await self.ai_client.chat(
                system=agent.system_prompt,
                message=prompt,
            )

            data = json.loads(response)
            challenges.append(DebateStatement(
                agent_name=agent.name,
                agent_role=agent.role,
                phase=DebatePhase.CHALLENGE,
                content=data["challenge"],
                signal=data["signal"],
                confidence=data["confidence"],
                target_agent=data.get("target_agent"),
            ))

        return challenges

    def _check_consensus(self, statements: list[DebateStatement]) -> bool:
        """Check if agents have reached consensus"""
        if not statements:
            return True

        signals = [s.signal for s in statements]
        # Map to numeric
        signal_map = {
            "strong_buy": 2, "buy": 1, "hold": 0, "sell": -1, "strong_sell": -2
        }
        values = [signal_map.get(s, 0) for s in signals]

        # Consensus if all agree on direction
        if all(v > 0 for v in values) or all(v < 0 for v in values) or all(v == 0 for v in values):
            return True

        return False

    async def _build_consensus(self, asset, all_statements):
        """Build final consensus from all debate rounds"""
        # Weight by confidence and recency
        signal_scores = {}
        for stmt in all_statements:
            if stmt.phase == DebatePhase.CONSENSUS:
                continue

            weight = stmt.confidence
            # More recent statements get higher weight
            if stmt.phase == DebatePhase.CHALLENGE:
                weight *= 1.2  # Post-debate opinions are more informed

            signal_map = {
                "strong_buy": 2, "buy": 1, "hold": 0, "sell": -1, "strong_sell": -2
            }
            score = signal_map.get(stmt.signal, 0) * weight

            if stmt.agent_name not in signal_scores:
                signal_scores[stmt.agent_name] = []
            signal_scores[stmt.agent_name].append(score)

        # Average each agent's final position, then average across agents
        agent_finals = {
            agent: scores[-1] if scores else 0
            for agent, scores in signal_scores.items()
        }
        avg_score = sum(agent_finals.values()) / max(len(agent_finals), 1)

        # Convert back to signal
        if avg_score > 1.2:
            final_signal = "strong_buy"
        elif avg_score > 0.3:
            final_signal = "buy"
        elif avg_score > -0.3:
            final_signal = "hold"
        elif avg_score > -1.2:
            final_signal = "sell"
        else:
            final_signal = "strong_sell"

        # Confidence based on agreement level
        scores = list(agent_finals.values())
        if scores:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            # Higher agreement → higher confidence
            confidence = max(0.2, min(0.95, 1.0 - (variance / 4.0)))
        else:
            confidence = 0.3

        reasoning_parts = []
        for stmt in all_statements:
            if stmt.phase in (DebatePhase.POSITION, DebatePhase.CHALLENGE):
                reasoning_parts.append(
                    f"{stmt.agent_name}: {stmt.signal} ({stmt.confidence:.0%}) — {stmt.content}"
                )

        num_agents = len(set(s.agent_name for s in all_statements))
        num_challenges = len([s for s in all_statements if s.phase == DebatePhase.CHALLENGE])
        consensus_text = (
            f"After {num_agents} agents debated "
            f"over {num_challenges} challenge rounds, "
            f"the consensus for {asset} is {final_signal.upper()} "
            f"(confidence: {confidence:.0%}). "
            f"Score: {avg_score:+.2f}."
        )

        return DebateStatement(
            agent_name="Arena Moderator",
            agent_role="Consensus Builder",
            phase=DebatePhase.CONSENSUS,
            content=consensus_text,
            signal=final_signal,
            confidence=confidence,
        )

    def _rule_based_analysis(self, agent, asset, market_data):
        """Fallback rule-based analysis when no AI client"""
        price = market_data.get("price", 0)
        rsi = market_data.get("rsi_14")
        sma_20 = market_data.get("sma_20")
        sma_200 = market_data.get("sma_200")

        if "Value" in agent.role or "Buffett" in agent.name:
            # Value: bearish if price >> SMA200, bullish if price << SMA200
            if sma_200 and price < sma_200 * 0.85:
                return DebateStatement(
                    agent_name=agent.name, agent_role=agent.role,
                    phase=DebatePhase.POSITION,
                    content=f"{asset} trades at ${price:,.0f}, {((price/sma_200)-1)*100:.1f}% "
                            f"below 200-day SMA (${sma_200:,.0f}). Deep value territory. "
                            f"Margin of safety exists.",
                    signal="buy", confidence=0.7,
                )
            elif sma_200 and price > sma_200 * 1.3:
                return DebateStatement(
                    agent_name=agent.name, agent_role=agent.role,
                    phase=DebatePhase.POSITION,
                    content=f"{asset} trades at ${price:,.0f}, {((price/sma_200)-1)*100:.1f}% "
                            f"above 200-day SMA. Overvalued. No margin of safety.",
                    signal="sell", confidence=0.6,
                )
            else:
                return DebateStatement(
                    agent_name=agent.name, agent_role=agent.role,
                    phase=DebatePhase.POSITION,
                    content=f"{asset} at ${price:,.0f} is fairly valued relative to "
                            f"long-term averages. No compelling opportunity.",
                    signal="hold", confidence=0.5,
                )

        elif "Quant" in agent.role or "Ada" in agent.name:
            # Quantitative: RSI + SMA + Bollinger signals
            signals = []
            factors = []
            if rsi is not None:
                if rsi < 30:
                    signals.append(1)
                    factors.append(f"RSI({rsi:.1f}) oversold")
                elif rsi > 70:
                    signals.append(-1)
                    factors.append(f"RSI({rsi:.1f}) overbought")
                else:
                    signals.append(0)
                    factors.append(f"RSI({rsi:.1f}) neutral")

            if sma_20 and price:
                pct = ((price / sma_20) - 1) * 100
                if price > sma_20:
                    signals.append(1)
                    factors.append(f"Price {pct:+.1f}% vs SMA20")
                else:
                    signals.append(-1)
                    factors.append(f"Price {pct:+.1f}% vs SMA20")

            if sma_200 and price:
                pct_200 = ((price / sma_200) - 1) * 100
                factors.append(f"Price {pct_200:+.1f}% vs SMA200")
                if price < sma_200 * 0.8:
                    signals.append(1)  # deeply oversold historically
                elif price > sma_200 * 1.2:
                    signals.append(-1)

            avg_signal = sum(signals) / max(len(signals), 1)
            if avg_signal > 0.3:
                signal, conf = "buy", 0.5 + avg_signal * 0.3
            elif avg_signal < -0.3:
                signal, conf = "sell", 0.5 + abs(avg_signal) * 0.3
            else:
                signal, conf = "hold", 0.4

            return DebateStatement(
                agent_name=agent.name, agent_role=agent.role,
                phase=DebatePhase.POSITION,
                content=f"Quantitative analysis for {asset}: {'; '.join(factors)}. "
                        f"Composite signal score: {avg_signal:+.2f}.",
                signal=signal, confidence=min(conf, 0.9),
            )

        else:
            return DebateStatement(
                agent_name=agent.name, agent_role=agent.role,
                phase=DebatePhase.POSITION,
                content=f"Neutral stance on {asset} at ${price:,.0f}.",
                signal="hold", confidence=0.3,
            )
