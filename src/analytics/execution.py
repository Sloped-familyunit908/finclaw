"""
FinClaw - Execution Analytics
Measure trade execution quality: slippage, market impact, VWAP comparison, timing.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionReport:
    order_id: str
    ticker: str
    side: str
    expected_price: float
    actual_price: float
    quantity: float
    slippage_bps: float        # basis points
    market_impact_bps: float
    vwap_diff_bps: float
    execution_delay_ms: float


class ExecutionAnalyzer:
    """Analyze trade execution quality."""

    def __init__(self):
        self._reports: list[ExecutionReport] = []

    def analyze_fill(
        self,
        order_id: str,
        ticker: str,
        side: str,
        expected_price: float,
        actual_price: float,
        quantity: float,
        vwap: Optional[float] = None,
        pre_trade_price: Optional[float] = None,
        post_trade_price: Optional[float] = None,
        signal_time_ms: Optional[float] = None,
        fill_time_ms: Optional[float] = None,
    ) -> ExecutionReport:
        """
        Analyze a single fill.

        Args:
            expected_price: Decision price (signal price)
            actual_price: Actual fill price
            vwap: Volume-weighted average price for the period
            pre_trade_price: Price before order entered market
            post_trade_price: Price after fill
            signal_time_ms: Timestamp of signal (epoch ms)
            fill_time_ms: Timestamp of fill (epoch ms)
        """
        sign = 1 if side == "buy" else -1

        # Slippage: how much worse was the fill vs expected
        slippage_bps = sign * (actual_price - expected_price) / expected_price * 10000

        # Market impact: price move from pre to post trade
        if pre_trade_price and post_trade_price:
            market_impact_bps = sign * (post_trade_price - pre_trade_price) / pre_trade_price * 10000
        else:
            market_impact_bps = 0.0

        # VWAP comparison
        if vwap and vwap > 0:
            vwap_diff_bps = sign * (actual_price - vwap) / vwap * 10000
        else:
            vwap_diff_bps = 0.0

        # Execution delay
        if signal_time_ms is not None and fill_time_ms is not None:
            execution_delay_ms = fill_time_ms - signal_time_ms
        else:
            execution_delay_ms = 0.0

        report = ExecutionReport(
            order_id=order_id,
            ticker=ticker,
            side=side,
            expected_price=expected_price,
            actual_price=actual_price,
            quantity=quantity,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            vwap_diff_bps=vwap_diff_bps,
            execution_delay_ms=execution_delay_ms,
        )
        self._reports.append(report)
        return report

    def get_summary(self) -> dict:
        """Aggregate execution quality stats."""
        if not self._reports:
            return {"n_trades": 0}

        slippages = [r.slippage_bps for r in self._reports]
        impacts = [r.market_impact_bps for r in self._reports]
        vwap_diffs = [r.vwap_diff_bps for r in self._reports]
        delays = [r.execution_delay_ms for r in self._reports if r.execution_delay_ms > 0]

        n = len(self._reports)
        return {
            "n_trades": n,
            "avg_slippage_bps": sum(slippages) / n,
            "max_slippage_bps": max(slippages),
            "avg_market_impact_bps": sum(impacts) / n,
            "avg_vwap_diff_bps": sum(vwap_diffs) / n,
            "avg_delay_ms": sum(delays) / len(delays) if delays else 0,
            "total_slippage_cost": sum(
                r.slippage_bps / 10000 * r.actual_price * r.quantity for r in self._reports
            ),
        }

    @property
    def reports(self) -> list[ExecutionReport]:
        return list(self._reports)
