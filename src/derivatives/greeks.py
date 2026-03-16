"""Portfolio-level Greeks aggregation and hedging recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from .options_pricing import BlackScholes


@dataclass
class OptionPosition:
    """A single option position in a portfolio.

    Attributes
    ----------
    option_type : 'call' or 'put'
    S : spot price
    K : strike price
    T : time to expiry (years)
    r : risk-free rate
    sigma : implied volatility
    quantity : number of contracts (negative = short)
    multiplier : contract multiplier (default 100 shares per contract)
    """

    option_type: str
    S: float
    K: float
    T: float
    r: float
    sigma: float
    quantity: int = 1
    multiplier: int = 100


class PortfolioGreeks:
    """Aggregate Greeks across a portfolio of option positions."""

    def calculate(self, positions: list[OptionPosition]) -> dict:
        """Compute net portfolio Greeks.

        Returns dict with net_delta, net_gamma, net_theta, net_vega,
        delta_by_expiry, gamma_by_strike.
        """
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        delta_by_expiry: dict[float, float] = {}
        gamma_by_strike: dict[float, float] = {}

        for pos in positions:
            g = BlackScholes.greeks(pos.S, pos.K, pos.T, pos.r, pos.sigma)
            scale = pos.quantity * pos.multiplier

            # Adjust delta sign for puts
            if pos.option_type.lower() == "put":
                pos_delta = (g["delta"] - 1.0) * scale
            else:
                pos_delta = g["delta"] * scale

            pos_gamma = g["gamma"] * scale
            pos_theta = g["theta"] * scale
            pos_vega = g["vega"] * scale

            net_delta += pos_delta
            net_gamma += pos_gamma
            net_theta += pos_theta
            net_vega += pos_vega

            delta_by_expiry[pos.T] = delta_by_expiry.get(pos.T, 0.0) + pos_delta
            gamma_by_strike[pos.K] = gamma_by_strike.get(pos.K, 0.0) + pos_gamma

        return {
            "net_delta": round(net_delta, 4),
            "net_gamma": round(net_gamma, 4),
            "net_theta": round(net_theta, 4),
            "net_vega": round(net_vega, 4),
            "delta_by_expiry": {k: round(v, 4) for k, v in delta_by_expiry.items()},
            "gamma_by_strike": {k: round(v, 4) for k, v in gamma_by_strike.items()},
        }

    def hedge_recommendation(self, positions: list[OptionPosition]) -> list[dict]:
        """Suggest trades to neutralize portfolio Greeks.

        Returns a list of recommended hedging actions.
        """
        greeks = self.calculate(positions)
        recommendations: list[dict] = []

        # Delta hedge with underlying shares
        if abs(greeks["net_delta"]) > 0.5:
            shares = -round(greeks["net_delta"])
            recommendations.append({
                "action": "buy" if shares > 0 else "sell",
                "instrument": "underlying_shares",
                "quantity": abs(shares),
                "reason": f"Delta neutralize: net_delta={greeks['net_delta']:.2f}",
            })

        # Gamma hedge suggestion
        if abs(greeks["net_gamma"]) > 0.01:
            recommendations.append({
                "action": "trade_options",
                "instrument": "ATM straddle",
                "direction": "buy" if greeks["net_gamma"] < 0 else "sell",
                "reason": f"Gamma hedge: net_gamma={greeks['net_gamma']:.4f}",
            })

        # Vega hedge suggestion
        if abs(greeks["net_vega"]) > 1.0:
            recommendations.append({
                "action": "trade_options",
                "instrument": "long-dated option",
                "direction": "buy" if greeks["net_vega"] < 0 else "sell",
                "reason": f"Vega hedge: net_vega={greeks['net_vega']:.2f}",
            })

        if not recommendations:
            recommendations.append({"action": "none", "reason": "Portfolio Greeks within acceptable bounds"})

        return recommendations
