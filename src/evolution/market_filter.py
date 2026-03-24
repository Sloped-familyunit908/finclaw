"""
Market State Safety Filter for Evolution Backtesting
=====================================================
Adjusts individual stock scores based on overall market conditions.

This is a HARD RULE applied post-scoring — not part of the evolved DNA.
The bottom_confirmation factors ARE part of evolution (they get weights),
but this filter always applies to prevent buying during market-wide crashes.

In a big crash day, reduce trust in buy signals.
In a confirmed bottom, boost buy signals.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


# Bottom confirmation factor names (used to detect bottom signals)
BOTTOM_FACTOR_NAMES = {
    "bottom_long_lower_shadow",
    "bottom_volume_decline_stabilize",
    "bottom_reversal_candle",
    "bottom_support_bounce",
    "bottom_consecutive_decline_exhaustion",
}


class MarketStateFilter:
    """Adjusts individual stock scores based on overall market conditions.

    In a big crash day, reduce trust in buy signals.
    In a confirmed bottom, boost buy signals.
    """

    def __init__(self, crash_lookback: int = 3, volume_lookback: int = 20):
        """Initialize the filter.

        Args:
            crash_lookback: Number of days to look back for crash detection.
            volume_lookback: Number of days for average volume calculation.
        """
        self.crash_lookback = crash_lookback
        self.volume_lookback = volume_lookback
        self._consecutive_crash_days = 0

    def compute_market_state(
        self,
        all_stock_data: Dict[str, Dict[str, list]],
        indicators: Dict[str, Dict[str, Any]],
        codes: List[str],
        current_day_idx: int,
    ) -> float:
        """Compute market state from the aggregate of all stocks.

        Returns:
            market_score: float in [0, 1]
              0.0 = extreme crash, don't buy anything
              0.5 = neutral
              1.0 = strong market, buy signals reliable

        Logic:
        - Count % of stocks declining today → if >70%, it's a crash day
        - Check if >70% declining for 3+ consecutive days → extended crash
        - Check if average RSI of universe < 25 → extreme oversold
        - Check if today's aggregate volume > 2x average → panic volume
        - After crash: check for reversal day (majority of stocks recovering)
        """
        if not codes or current_day_idx < 2:
            return 0.5  # neutral when insufficient data

        # Count declining stocks today
        total_valid = 0
        declining_count = 0
        rsi_values = []
        volume_spike_count = 0

        for code in codes:
            sd = all_stock_data.get(code, {})
            closes = sd.get("close", [])
            volumes = sd.get("volume", [])

            if current_day_idx >= len(closes) or current_day_idx < 1:
                continue

            total_valid += 1

            # Check if declining today
            if closes[current_day_idx] < closes[current_day_idx - 1]:
                declining_count += 1

            # Collect RSI values
            ind = indicators.get(code, {})
            rsi_arr = ind.get("rsi", [])
            if current_day_idx < len(rsi_arr):
                rsi_val = rsi_arr[current_day_idx]
                if not (isinstance(rsi_val, float) and math.isnan(rsi_val)):
                    rsi_values.append(rsi_val)

            # Check volume spike
            if current_day_idx >= self.volume_lookback and len(volumes) > current_day_idx:
                avg_vol = sum(
                    volumes[current_day_idx - self.volume_lookback:current_day_idx]
                ) / self.volume_lookback
                if avg_vol > 0 and volumes[current_day_idx] > 2.0 * avg_vol:
                    volume_spike_count += 1

        if total_valid == 0:
            return 0.5

        # Percentage of stocks declining
        decline_pct = declining_count / total_valid

        # Start with neutral score
        score = 0.5

        # ── Factor 1: Decline breadth ──
        if decline_pct > 0.7:
            # Crash day: >70% of stocks declining
            score -= 0.25
            self._consecutive_crash_days += 1
        elif decline_pct > 0.6:
            # Many stocks declining
            score -= 0.1
            self._consecutive_crash_days = max(0, self._consecutive_crash_days - 1)
        elif decline_pct < 0.3:
            # Strong market: <30% declining (most stocks rising)
            score += 0.2
            self._consecutive_crash_days = 0
        elif decline_pct < 0.4:
            # Mild strength
            score += 0.1
            self._consecutive_crash_days = 0
        else:
            # Neutral breadth
            self._consecutive_crash_days = 0

        # ── Factor 2: Extended crash (3+ consecutive crash days) ──
        if self._consecutive_crash_days >= 3:
            score -= 0.15  # extended crash penalty

        # ── Factor 3: Average RSI of universe ──
        if rsi_values:
            avg_rsi = sum(rsi_values) / len(rsi_values)
            if avg_rsi < 25:
                # Extreme oversold — panic territory
                score -= 0.15
            elif avg_rsi < 35:
                # Moderately oversold
                score -= 0.05
            elif avg_rsi > 65:
                # Overbought but market is strong
                score += 0.1

        # ── Factor 4: Panic volume ──
        if total_valid > 0:
            volume_spike_pct = volume_spike_count / total_valid
            if volume_spike_pct > 0.5:
                # Many stocks with volume spikes — panic selling or capitulation
                score -= 0.1

        # ── Factor 5: Reversal detection ──
        # If we had crash days recently but today shows recovery
        if self._consecutive_crash_days >= 2 and decline_pct < 0.4:
            # Reversal day after crash — potentially bullish
            score += 0.1
            self._consecutive_crash_days = 0

        return max(0.0, min(1.0, score))

    def adjust_score(
        self,
        raw_score: float,
        market_state: float,
        has_bottom_signal: bool,
    ) -> float:
        """Adjust individual stock score based on market state.

        This is the HARD RULE that prevents buying during crashes.
        Applied post-scoring, not subject to evolution.

        Rules:
        - If market_state < 0.2 (extreme crash): score *= 0.3 regardless
        - If market_state < 0.3 (crash) AND no bottom_signal: score *= 0.5
        - If market_state < 0.3 AND has bottom_signal: score *= 0.8
        - If market_state > 0.7 (strong market): score unchanged
        - Otherwise (0.3-0.7, neutral): mild adjustment

        Args:
            raw_score: Original stock score from score_stock()
            market_state: Market state from compute_market_state() [0, 1]
            has_bottom_signal: Whether this stock has bottom confirmation factors firing

        Returns:
            Adjusted score
        """
        if market_state < 0.2:
            # Extreme crash — reduce all scores heavily regardless of signals
            return raw_score * 0.3

        if market_state < 0.3:
            # Crash — reduce scores, but less if bottom signals are present
            if has_bottom_signal:
                return raw_score * 0.8
            else:
                return raw_score * 0.5

        if market_state < 0.4:
            # Weak market
            if has_bottom_signal:
                return raw_score * 0.9
            else:
                return raw_score * 0.7

        if market_state > 0.7:
            # Strong market — no adjustment needed
            return raw_score

        # Neutral market (0.4 - 0.7) — mild adjustment
        # Linear interpolation: at 0.4 apply 0.85x, at 0.7 apply 1.0x
        factor = 0.85 + (market_state - 0.4) / 0.3 * 0.15
        return raw_score * factor

    @staticmethod
    def check_bottom_signals(
        indicators: Dict[str, Any],
        closes: list,
        highs: list,
        lows: list,
        volumes: list,
        idx: int,
    ) -> bool:
        """Check if a stock has any bottom confirmation factor signals firing.

        A bottom signal is considered "firing" if any bottom_confirmation factor
        returns a score >= 0.7 (bullish signal).

        Args:
            indicators: Pre-computed indicators dict for this stock
            closes, highs, lows, volumes: Price/volume data
            idx: Current day index

        Returns:
            True if at least one bottom factor is firing
        """
        factor_fns = indicators.get("_factor_fns", {})

        for fname in BOTTOM_FACTOR_NAMES:
            fn = factor_fns.get(fname)
            if fn is None:
                continue
            try:
                val = fn(closes, highs, lows, volumes, idx)
                if val >= 0.7:
                    return True
            except Exception:
                continue

        return False
