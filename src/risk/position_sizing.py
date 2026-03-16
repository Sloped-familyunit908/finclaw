"""
Position Sizing Algorithms
Kelly Criterion, Fixed Fractional, Volatility-based.
"""

import math
from dataclasses import dataclass


@dataclass
class PositionSize:
    fraction: float   # fraction of capital to risk (0-1)
    reason: str


class KellyCriterion:
    """
    Kelly criterion: f* = (bp - q) / b
    where b = odds (avg_win / avg_loss), p = win_rate, q = 1-p
    
    Uses half-Kelly by default for safety.
    """

    def __init__(self, kelly_fraction: float = 0.5, max_position: float = 0.25):
        self.kelly_fraction = kelly_fraction
        self.max_position = max_position

    def calculate(self, win_rate: float, avg_win: float, avg_loss: float) -> PositionSize:
        if avg_loss == 0 or win_rate <= 0:
            return PositionSize(0, "no edge detected")

        b = abs(avg_win / avg_loss)  # odds ratio
        p = win_rate
        q = 1 - p

        kelly = (b * p - q) / b
        if kelly <= 0:
            return PositionSize(0, f"negative edge: kelly={kelly:.3f}")

        adjusted = kelly * self.kelly_fraction
        final = min(adjusted, self.max_position)
        return PositionSize(
            final,
            f"kelly={kelly:.3f}, {self.kelly_fraction:.0%}-kelly={adjusted:.3f}, capped={final:.3f}"
        )


class FixedFractional:
    """Risk a fixed fraction of capital per trade."""

    def __init__(self, risk_per_trade: float = 0.02):
        self.risk_per_trade = risk_per_trade

    def calculate(self, capital: float, entry_price: float, stop_price: float) -> PositionSize:
        risk_amount = capital * self.risk_per_trade
        price_risk = abs(entry_price - stop_price)
        if price_risk == 0:
            return PositionSize(0, "zero price risk")

        shares = risk_amount / price_risk
        position_value = shares * entry_price
        fraction = position_value / capital if capital > 0 else 0

        return PositionSize(
            min(fraction, 1.0),
            f"risk ${risk_amount:.0f} at {self.risk_per_trade:.1%}, "
            f"stop distance={price_risk:.2f}"
        )


class VolatilitySizing:
    """
    Position size inversely proportional to volatility.
    Targets a fixed dollar volatility per position.
    """

    def __init__(self, target_volatility: float = 0.01, max_position: float = 0.30):
        self.target_volatility = target_volatility
        self.max_position = max_position

    def calculate(self, capital: float, prices: list[float], atr: float = None) -> PositionSize:
        if not prices or len(prices) < 2:
            return PositionSize(0, "insufficient data")

        if atr is None:
            # Compute simple ATR proxy from daily returns
            rets = [abs(prices[i] / prices[i-1] - 1) for i in range(1, len(prices))]
            atr_pct = sum(rets[-14:]) / min(14, len(rets)) if rets else 0.02
        else:
            atr_pct = atr / prices[-1] if prices[-1] > 0 else 0.02

        if atr_pct == 0:
            return PositionSize(0, "zero volatility")

        fraction = self.target_volatility / atr_pct
        final = min(fraction, self.max_position)
        return PositionSize(final, f"vol={atr_pct:.3f}, target_vol={self.target_volatility:.3f}")
