"""Risk Budgeting — allocate, measure, and rebalance risk across assets."""

from __future__ import annotations

import math
from typing import Dict, List


class RiskBudgeter:
    """Risk budget allocation and contribution analysis."""

    def allocate(self, target_vol: float, assets: dict) -> dict:
        """Allocate risk budget across assets based on their volatilities.

        Args:
            target_vol: Target portfolio volatility (annualized, e.g. 0.15 = 15%).
            assets: Dict of asset_name -> {'vol': annualized_vol, 'weight': current_weight}.

        Returns:
            Dict of asset_name -> allocated risk budget (vol contribution).
        """
        if not assets or target_vol <= 0:
            return {}

        total_weighted_vol = sum(a['vol'] * a['weight'] for a in assets.values())
        if total_weighted_vol == 0:
            # Equal risk budget
            equal_share = target_vol / len(assets)
            return {name: round(equal_share, 6) for name in assets}

        budget = {}
        for name, info in assets.items():
            share = (info['vol'] * info['weight']) / total_weighted_vol
            budget[name] = round(share * target_vol, 6)
        return budget

    def marginal_risk(self, portfolio: dict, asset: str) -> float:
        """Marginal risk contribution of an asset.

        Args:
            portfolio: Dict of asset_name -> {'vol': float, 'weight': float}.
            asset: Asset to measure.

        Returns:
            Marginal risk contribution.
        """
        if asset not in portfolio:
            return 0.0

        info = portfolio[asset]
        port_vol = self._portfolio_vol(portfolio)
        if port_vol == 0:
            return 0.0

        # Marginal = weight * vol^2 / portfolio_vol (simplified, assumes no correlation)
        return info['weight'] * info['vol'] ** 2 / port_vol

    def risk_contribution(self, portfolio: dict) -> dict:
        """Risk contribution of each asset in the portfolio.

        Args:
            portfolio: Dict of asset_name -> {'vol': float, 'weight': float}.

        Returns:
            Dict of asset_name -> {'risk_contribution': float, 'pct_of_total': float}.
        """
        if not portfolio:
            return {}

        port_vol = self._portfolio_vol(portfolio)
        if port_vol == 0:
            return {name: {'risk_contribution': 0.0, 'pct_of_total': 0.0} for name in portfolio}

        contributions = {}
        total_rc = 0.0
        raw = {}
        for name, info in portfolio.items():
            rc = info['weight'] ** 2 * info['vol'] ** 2
            raw[name] = rc
            total_rc += rc

        for name, rc in raw.items():
            pct = rc / total_rc if total_rc > 0 else 0.0
            contributions[name] = {
                'risk_contribution': round(math.sqrt(rc), 6),
                'pct_of_total': round(pct * 100, 2),
            }
        return contributions

    def rebalance_to_risk_target(self, portfolio: dict, target: dict) -> list:
        """Generate rebalancing trades to match target risk allocation.

        Args:
            portfolio: Current asset_name -> {'vol': float, 'weight': float}.
            target: asset_name -> target_risk_pct (must sum to ~100).

        Returns:
            List of dicts with asset, action, weight_change.
        """
        if not portfolio or not target:
            return []

        current_rc = self.risk_contribution(portfolio)
        trades = []

        for asset, target_pct in target.items():
            current_pct = current_rc.get(asset, {}).get('pct_of_total', 0.0)
            diff = target_pct - current_pct
            if abs(diff) < 0.5:
                continue

            current_weight = portfolio.get(asset, {}).get('weight', 0.0)
            # Scale weight proportionally to risk gap
            weight_change = current_weight * (diff / 100) if current_pct > 0 else diff / 100
            trades.append({
                'asset': asset,
                'action': 'increase' if diff > 0 else 'decrease',
                'weight_change': round(weight_change, 4),
                'current_risk_pct': current_pct,
                'target_risk_pct': target_pct,
            })

        return trades

    @staticmethod
    def _portfolio_vol(portfolio: dict) -> float:
        """Simplified portfolio vol (assumes zero correlation)."""
        var = sum((info['weight'] * info['vol']) ** 2 for info in portfolio.values())
        return math.sqrt(var)
