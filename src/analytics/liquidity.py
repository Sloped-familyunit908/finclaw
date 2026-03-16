"""Liquidity Analysis — volume, spread estimation, and Amihud illiquidity."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class LiquidityData:
    """OHLCV data point for liquidity analysis."""
    close: float
    volume: int
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0


class LiquidityAnalyzer:
    """Analyze stock and portfolio liquidity characteristics."""

    def analyze(self, ticker: str, data: List[LiquidityData]) -> dict:
        """Compute liquidity metrics for a single ticker.

        Args:
            ticker: Stock ticker symbol.
            data: List of LiquidityData (daily bars).

        Returns:
            Dict with avg_volume, avg_dollar_volume, bid_ask_spread_est,
            amihud_illiquidity, turnover_ratio, days_to_liquidate.
        """
        if not data:
            return self._empty_result(ticker)

        volumes = [d.volume for d in data]
        avg_volume = sum(volumes) / len(volumes)

        dollar_volumes = [d.close * d.volume for d in data]
        avg_dollar_volume = sum(dollar_volumes) / len(dollar_volumes)

        # Bid-ask spread estimation (Corwin-Schultz high-low estimator simplified)
        spreads = []
        for d in data:
            if d.high > 0 and d.low > 0 and d.high != d.low:
                spread = 2 * (d.high - d.low) / (d.high + d.low)
                spreads.append(spread)
        bid_ask_spread_est = sum(spreads) / len(spreads) if spreads else 0.0

        # Amihud illiquidity ratio
        amihud_vals = []
        for i in range(1, len(data)):
            if data[i].close > 0 and data[i - 1].close > 0 and dollar_volumes[i] > 0:
                ret = abs(data[i].close - data[i - 1].close) / data[i - 1].close
                amihud_vals.append(ret / dollar_volumes[i])
        amihud_illiquidity = sum(amihud_vals) / len(amihud_vals) if amihud_vals else 0.0

        # Turnover ratio (assuming shares outstanding ~ 10x avg volume as rough proxy)
        shares_outstanding_est = avg_volume * 10
        turnover_ratio = avg_volume / shares_outstanding_est if shares_outstanding_est > 0 else 0.0

        # Days to liquidate 10% of avg daily volume
        position_shares = avg_volume * 0.1
        days_to_liquidate = position_shares / (avg_volume * 0.1) if avg_volume > 0 else float('inf')

        return {
            'ticker': ticker,
            'avg_volume': round(avg_volume, 0),
            'avg_dollar_volume': round(avg_dollar_volume, 2),
            'bid_ask_spread_est': round(bid_ask_spread_est, 6),
            'amihud_illiquidity': amihud_illiquidity,
            'turnover_ratio': round(turnover_ratio, 4),
            'days_to_liquidate': round(days_to_liquidate, 2),
        }

    def portfolio_liquidity(self, holdings: Dict[str, dict]) -> dict:
        """Aggregate liquidity across portfolio holdings.

        Args:
            holdings: Dict of ticker -> {'weight': float, 'liquidity': dict from analyze()}.

        Returns:
            Portfolio-level liquidity summary.
        """
        if not holdings:
            return {'weighted_spread': 0.0, 'weighted_amihud': 0.0, 'max_days_to_liquidate': 0.0, 'holdings': 0}

        weighted_spread = 0.0
        weighted_amihud = 0.0
        max_days = 0.0
        total_dollar_vol = 0.0

        for ticker, info in holdings.items():
            w = info.get('weight', 0.0)
            liq = info.get('liquidity', {})
            weighted_spread += w * liq.get('bid_ask_spread_est', 0.0)
            weighted_amihud += w * liq.get('amihud_illiquidity', 0.0)
            max_days = max(max_days, liq.get('days_to_liquidate', 0.0))
            total_dollar_vol += liq.get('avg_dollar_volume', 0.0) * w

        return {
            'weighted_spread': round(weighted_spread, 6),
            'weighted_amihud': weighted_amihud,
            'max_days_to_liquidate': round(max_days, 2),
            'total_weighted_dollar_volume': round(total_dollar_vol, 2),
            'holdings': len(holdings),
        }

    @staticmethod
    def _empty_result(ticker: str) -> dict:
        return {
            'ticker': ticker,
            'avg_volume': 0, 'avg_dollar_volume': 0.0,
            'bid_ask_spread_est': 0.0, 'amihud_illiquidity': 0.0,
            'turnover_ratio': 0.0, 'days_to_liquidate': 0.0,
        }
