"""
FinClaw - Constitutional Risk Management
Inspired by Anthropic's Constitutional AI applied to finance.

These rules CANNOT be overridden by debate consensus.
They are the "laws of physics" of the trading system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VetoReason(Enum):
    MAX_POSITION_SIZE = "Position size exceeds maximum allowed"
    MAX_DRAWDOWN = "Portfolio drawdown exceeds halt threshold"
    MAX_DAILY_LOSS = "Daily loss exceeds maximum allowed"
    HIGH_CORRELATION = "New position too correlated with existing"
    LOW_CONFIDENCE = "Debate confidence below minimum threshold"
    LEVERAGE_LIMIT = "Leverage exceeds maximum allowed"
    COOLDOWN_PERIOD = "In cooldown period after large loss"
    MAX_OPEN_POSITIONS = "Maximum number of open positions reached"


@dataclass
class RiskConstitution:
    """
    Immutable risk rules. Guardian Agent enforces these.
    These CANNOT be overridden by debate consensus.
    
    Philosophy: Like a nation's constitution, these rules protect
    the system from its own impulses.
    """
    
    # Position limits
    max_position_pct: float = 0.20          # Max 20% of capital per position
    max_open_positions: int = 5              # Max simultaneous positions
    max_total_exposure_pct: float = 0.95     # Max 95% invested (keep 5% cash)
    
    # Drawdown protection
    max_drawdown_halt: float = -0.15         # Halt all trading at -15%
    max_daily_loss: float = -0.05            # Halt for today at -5%
    cooldown_hours_after_halt: int = 24      # Wait 24h after halt
    
    # Correlation limits
    max_position_correlation: float = 0.80   # Don't stack correlated bets
    
    # Debate confidence threshold
    min_debate_confidence: float = 0.55      # Don't trade on weak consensus
    min_agents_agreeing: int = 2             # At least 2 agents must agree
    
    # Leverage
    max_leverage: float = 1.0                # No leverage in v1
    
    # Per-trade risk
    max_loss_per_trade_pct: float = 0.05     # Max 5% loss per trade (stop-loss)
    required_risk_reward: float = 1.5        # Minimum 1.5:1 reward-to-risk


@dataclass
class RiskCheckResult:
    """Result of a constitutional risk check"""
    approved: bool
    vetoed_by: Optional[VetoReason] = None
    adjusted_position_size: Optional[float] = None
    required_stop_loss: Optional[float] = None
    explanation: str = ""


class ConstitutionalGuardian:
    """
    The Guardian enforces the Risk Constitution.
    No debate, no override, no exceptions.
    
    Like the Supreme Court, it has final say on risk matters.
    """

    def __init__(self, constitution: RiskConstitution = None):
        self.constitution = constitution or RiskConstitution()
        self.daily_pnl: float = 0.0
        self.peak_equity: float = 0.0
        self.current_equity: float = 0.0
        self.is_halted: bool = False
        self.halt_reason: Optional[str] = None
        self.open_positions: list[dict] = []

    def check_trade(self, signal: str, confidence: float,
                    position_size_pct: float,
                    current_equity: float,
                    num_agents_agreeing: int = 0) -> RiskCheckResult:
        """
        Constitutional check before any trade execution.
        Returns approval or veto with explanation.
        """
        c = self.constitution
        self.current_equity = current_equity

        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # ── Check 1: System halt ──
        if self.is_halted:
            return RiskCheckResult(
                approved=False,
                vetoed_by=VetoReason.MAX_DRAWDOWN,
                explanation=f"SYSTEM HALTED: {self.halt_reason}. "
                           f"Wait {c.cooldown_hours_after_halt}h before resuming."
            )

        # ── Check 2: Drawdown halt ──
        if self.peak_equity > 0:
            current_dd = (current_equity - self.peak_equity) / self.peak_equity
            if current_dd <= c.max_drawdown_halt:
                self.is_halted = True
                self.halt_reason = (f"Drawdown {current_dd:.1%} exceeded "
                                   f"maximum {c.max_drawdown_halt:.1%}")
                return RiskCheckResult(
                    approved=False,
                    vetoed_by=VetoReason.MAX_DRAWDOWN,
                    explanation=f"🛑 EMERGENCY HALT: {self.halt_reason}"
                )

        # ── Check 3: Daily loss limit ──
        if self.daily_pnl <= c.max_daily_loss * self.peak_equity:
            return RiskCheckResult(
                approved=False,
                vetoed_by=VetoReason.MAX_DAILY_LOSS,
                explanation=f"Daily loss {self.daily_pnl:.2f} exceeded limit. "
                           f"Trading paused until tomorrow."
            )

        # ── Check 4: Hold signals don't need checks ──
        if signal in ("hold",):
            return RiskCheckResult(approved=True, explanation="HOLD — no action needed")

        # ── Check 5: Confidence threshold ──
        if confidence < c.min_debate_confidence:
            return RiskCheckResult(
                approved=False,
                vetoed_by=VetoReason.LOW_CONFIDENCE,
                explanation=f"Debate confidence {confidence:.1%} below minimum "
                           f"{c.min_debate_confidence:.1%}. Not enough conviction."
            )

        # ── Check 6: Minimum agent agreement ──
        if num_agents_agreeing < c.min_agents_agreeing:
            return RiskCheckResult(
                approved=False,
                vetoed_by=VetoReason.LOW_CONFIDENCE,
                explanation=f"Only {num_agents_agreeing} agents agree, "
                           f"need at least {c.min_agents_agreeing}."
            )

        # ── Check 7: Position size ──
        adjusted_size = min(position_size_pct, c.max_position_pct)
        
        # ── Check 8: Max open positions ──
        if len(self.open_positions) >= c.max_open_positions:
            return RiskCheckResult(
                approved=False,
                vetoed_by=VetoReason.MAX_OPEN_POSITIONS,
                explanation=f"Already have {len(self.open_positions)} open positions "
                           f"(max {c.max_open_positions}). Close one first."
            )

        # ── Check 9: Total exposure ──
        total_exposure = sum(p.get("size_pct", 0) for p in self.open_positions)
        if total_exposure + adjusted_size > c.max_total_exposure_pct:
            adjusted_size = max(0, c.max_total_exposure_pct - total_exposure)
            if adjusted_size < 0.05:  # Less than 5% not worth it
                return RiskCheckResult(
                    approved=False,
                    vetoed_by=VetoReason.MAX_POSITION_SIZE,
                    explanation=f"Total exposure would exceed {c.max_total_exposure_pct:.0%}. "
                               f"Available: {adjusted_size:.1%}."
                )

        # ── All checks passed ──
        # Calculate required stop-loss
        stop_loss_distance = c.max_loss_per_trade_pct
        
        return RiskCheckResult(
            approved=True,
            adjusted_position_size=adjusted_size,
            required_stop_loss=stop_loss_distance,
            explanation=f"✅ APPROVED: {signal.upper()} with {adjusted_size:.1%} position, "
                       f"stop-loss at {stop_loss_distance:.1%}."
        )

    def record_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        self.daily_pnl += pnl

    def reset_daily(self):
        """Reset daily counters (call at market open)"""
        self.daily_pnl = 0.0

    def resume_trading(self):
        """Resume after halt (requires manual confirmation)"""
        self.is_halted = False
        self.halt_reason = None

    def get_status(self) -> str:
        """Get current risk status"""
        dd = 0
        if self.peak_equity > 0:
            dd = (self.current_equity - self.peak_equity) / self.peak_equity
        
        status = "🔴 HALTED" if self.is_halted else "🟢 ACTIVE"
        return (
            f"  Guardian Status: {status}\n"
            f"  Peak Equity:     ${self.peak_equity:,.2f}\n"
            f"  Current Equity:  ${self.current_equity:,.2f}\n"
            f"  Drawdown:        {dd:.2%}\n"
            f"  Daily P&L:       ${self.daily_pnl:,.2f}\n"
            f"  Open Positions:  {len(self.open_positions)}/{self.constitution.max_open_positions}\n"
        )
