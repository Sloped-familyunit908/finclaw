"""
Reversal Pattern Strategies - U and V Shape Reversals
====================================================
Two classic reversal patterns for A-share short-term trading.

U Shape: Slow decline → sideways consolidation → breakout
V Shape: Sharp decline → immediate bounce with RSI confirmation

These strategies run PARALLEL to existing strategies — no existing code is modified.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UShapeSignal:
    """A U-shape reversal buy signal."""
    date_idx: int          # Index of the breakout day (signal day)
    decline_start_idx: int # Where the decline began
    bottom_start_idx: int  # Where the bottom consolidation started
    buy_price: float       # T+1 open price
    decline_pct: float     # Total decline percentage
    decline_days: int      # How many days of decline
    consolidation_days: int  # How many days of consolidation
    breakout_volume_ratio: float  # Breakout volume / avg consolidation volume
    score: float           # Signal quality 0-100


@dataclass
class VShapeSignal:
    """A V-shape reversal buy signal."""
    date_idx: int        # Index of the bounce confirmation day
    decline_start_idx: int  # Where the decline began
    bottom_idx: int      # Index of the V bottom
    buy_price: float     # T+1 open price
    decline_pct: float   # Total decline percentage
    decline_days: int    # How many days of decline
    rsi_at_bottom: float # RSI at the bottom
    rsi_current: float   # RSI at signal day
    score: float         # Signal quality 0-100


class UShapeReversal:
    """U型反转 strategy.

    Pattern:
      1. Continuous decline for 5+ days with >15% total drop
      2. Sideways consolidation at bottom for 3-5 days (low amplitude, low R²)
      3. Volume breakout above consolidation range
      4. Buy at T+1 open, target: return to decline start price

    Parameters:
        min_decline_days:     Minimum days of decline (default 5)
        min_decline_pct:      Minimum total decline percentage (default 15.0)
        min_consolidation_days: Minimum sideways days (default 3)
        max_consolidation_days: Maximum sideways days (default 5)
        max_consolidation_range: Max high-low range during consolidation as % (default 5.0)
        min_breakout_volume:  Minimum breakout volume vs avg consolidation volume (default 1.5)
        tp_pct:               Take profit: target % toward decline start price (default 80.0)
        sl_pct:               Stop loss below consolidation low (default 5.0)
        max_hold_days:        Max holding days (default 15)
    """

    def __init__(
        self,
        min_decline_days: int = 5,
        min_decline_pct: float = 15.0,
        min_consolidation_days: int = 3,
        max_consolidation_days: int = 5,
        max_consolidation_range: float = 5.0,
        min_breakout_volume: float = 1.5,
        tp_pct: float = 80.0,
        sl_pct: float = 5.0,
        max_hold_days: int = 15,
    ):
        self.min_decline_days = min_decline_days
        self.min_decline_pct = min_decline_pct
        self.min_consolidation_days = min_consolidation_days
        self.max_consolidation_days = max_consolidation_days
        self.max_consolidation_range = max_consolidation_range
        self.min_breakout_volume = min_breakout_volume
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.max_hold_days = max_hold_days

    @staticmethod
    def calculate_r2(prices: np.ndarray) -> float:
        """R-squared (trend linearity) for a price segment.

        Returns 0.0 when there is insufficient data or zero variance.
        """
        prices = np.asarray(prices, dtype=np.float64)
        n = len(prices)
        if n < 2:
            return 0.0
        x = np.arange(n, dtype=np.float64)
        y_mean = np.mean(prices)
        ss_tot = np.sum((prices - y_mean) ** 2)
        if ss_tot == 0:
            return 0.0
        x_mean = np.mean(x)
        slope = np.sum((x - x_mean) * (prices - y_mean)) / np.sum((x - x_mean) ** 2)
        intercept = y_mean - slope * x_mean
        y_pred = slope * x + intercept
        ss_res = np.sum((prices - y_pred) ** 2)
        r2 = 1.0 - ss_res / ss_tot
        return max(r2, 0.0)

    def find_decline_phases(
        self,
        closes: np.ndarray,
    ) -> List[tuple]:
        """Find continuous decline phases.

        A decline phase is a sequence of days where the overall trend is clearly down.
        We look for stretches where the price drops at least min_decline_pct%.

        Returns list of (start_idx, end_idx, decline_pct).
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        results = []

        i = 0
        while i < n - self.min_decline_days:
            # Find a peak (local high)
            peak_idx = i
            peak_price = closes[i]

            # Walk forward looking for a trough
            lowest_idx = i
            lowest_price = peak_price

            for j in range(i + 1, min(i + 30, n)):  # Look up to 30 days ahead
                if closes[j] < lowest_price:
                    lowest_price = closes[j]
                    lowest_idx = j
                elif closes[j] > peak_price * 0.98:
                    # Price recovered, this decline is over
                    break

            decline_days = lowest_idx - peak_idx
            if decline_days >= self.min_decline_days and peak_price > 0:
                decline_pct = (1.0 - lowest_price / peak_price) * 100.0
                if decline_pct >= self.min_decline_pct:
                    results.append((peak_idx, lowest_idx, decline_pct))
                    i = lowest_idx + 1
                    continue

            i += 1

        return results

    def find_signals(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
    ) -> List[UShapeSignal]:
        """Find U-shape reversal signals.

        Returns list of UShapeSignal.
        """
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        decline_phases = self.find_decline_phases(closes)
        signals = []

        for decline_start, decline_end, decline_pct in decline_phases:
            # After decline, look for consolidation
            for cons_days in range(self.min_consolidation_days, self.max_consolidation_days + 1):
                cons_end = decline_end + cons_days
                breakout_idx = cons_end  # The breakout day
                buy_idx = breakout_idx + 1

                if buy_idx >= n:
                    continue

                cons_slice = slice(decline_end, cons_end)
                cons_highs = highs[cons_slice]
                cons_lows = lows[cons_slice]
                cons_closes = closes[cons_slice]
                cons_volumes = volumes[cons_slice]

                if len(cons_closes) != cons_days:
                    continue

                # Check consolidation range (high-low range should be small)
                if len(cons_lows) == 0:
                    continue
                cons_low = np.min(cons_lows)
                cons_high = np.max(cons_highs)
                if cons_low <= 0:
                    continue
                cons_range = (cons_high - cons_low) / cons_low * 100.0
                if cons_range > self.max_consolidation_range:
                    continue

                # Check R² of consolidation (should be low = sideways)
                r2 = self.calculate_r2(cons_closes)
                if r2 > 0.5:
                    continue  # Too trendy, not sideways

                # Check breakout: price breaks above consolidation high
                if closes[breakout_idx] <= cons_high:
                    continue

                # Check volume breakout
                avg_cons_vol = np.mean(cons_volumes)
                if avg_cons_vol <= 0:
                    continue
                breakout_vol_ratio = volumes[breakout_idx] / avg_cons_vol
                if breakout_vol_ratio < self.min_breakout_volume:
                    continue

                # Score
                score = min(100.0, 
                    min(40.0, decline_pct * 2.0) +    # Bigger decline = better setup
                    min(30.0, breakout_vol_ratio * 10.0) +  # Stronger breakout = better
                    max(0.0, (0.5 - r2) * 40.0) +    # Flatter consolidation = better
                    max(0.0, (self.max_consolidation_range - cons_range) * 2.0)
                )

                buy_price = opens[buy_idx]
                if buy_price <= 0:
                    continue

                signals.append(UShapeSignal(
                    date_idx=breakout_idx,
                    decline_start_idx=decline_start,
                    bottom_start_idx=decline_end,
                    buy_price=buy_price,
                    decline_pct=round(decline_pct, 2),
                    decline_days=decline_end - decline_start,
                    consolidation_days=cons_days,
                    breakout_volume_ratio=round(breakout_vol_ratio, 2),
                    score=round(score, 1),
                ))
                break  # Found valid signal for this decline, stop

        return signals

    def backtest(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        initial_capital: float = 1_000_000.0,
        code: str = "",
    ) -> dict:
        """Backtest U-shape reversal strategy on one stock."""
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        signals = self.find_signals(opens, highs, lows, closes, volumes, code)
        trades = []
        capital = initial_capital
        position_end = -1

        for sig in signals:
            buy_idx = sig.date_idx + 1
            if buy_idx <= position_end or buy_idx >= n:
                continue

            entry_price = sig.buy_price
            if entry_price <= 0:
                continue

            # Target: tp_pct% of the way back to decline start price
            decline_start_price = closes[sig.decline_start_idx]
            tp_price = entry_price * (1.0 + (decline_start_price / entry_price - 1.0) * self.tp_pct / 100.0)
            sl_price = entry_price * (1.0 - self.sl_pct / 100.0)

            exit_price = None
            exit_reason = None
            exit_idx = None

            for day in range(buy_idx, min(buy_idx + self.max_hold_days, n)):
                if lows[day] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "stop_loss"
                    exit_idx = day
                    break
                if highs[day] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "take_profit"
                    exit_idx = day
                    break

            if exit_price is None:
                last_day = min(buy_idx + self.max_hold_days - 1, n - 1)
                exit_price = closes[last_day]
                exit_reason = "max_hold"
                exit_idx = last_day

            position_end = exit_idx
            return_pct = (exit_price / entry_price - 1.0) * 100.0
            capital *= (1.0 + return_pct / 100.0)

            trades.append({
                "entry_idx": buy_idx,
                "exit_idx": exit_idx,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "return_pct": round(return_pct, 2),
                "exit_reason": exit_reason,
                "hold_days": exit_idx - buy_idx + 1,
                "decline_pct": sig.decline_pct,
                "consolidation_days": sig.consolidation_days,
            })

        returns = [t["return_pct"] for t in trades]
        winning = [r for r in returns if r > 0]

        return {
            "code": code,
            "trades": trades,
            "total_trades": len(trades),
            "total_return": round((capital / initial_capital - 1.0) * 100.0, 2) if trades else 0.0,
            "win_rate": round(len(winning) / len(trades) * 100.0, 2) if trades else 0.0,
            "avg_return": round(float(np.mean(returns)), 2) if returns else 0.0,
        }


class VShapeReversal:
    """V型反转 strategy.

    Pattern:
      1. Rapid decline: 3+ days with >10% total drop
      2. Immediate bounce (no sideways consolidation)
      3. RSI drops from below 20 and quickly recovers above 40
      4. Buy at T+1 open, target: previous high

    Parameters:
        min_decline_days:    Min days of rapid decline (default 3)
        max_decline_days:    Max days of decline (default 5, V shape is fast)
        min_decline_pct:     Min total decline percentage (default 10.0)
        rsi_bottom:          RSI must go below this (default 20.0)
        rsi_recovery:        RSI must recover above this (default 40.0)
        rsi_period:          RSI calculation period (default 14)
        tp_pct:              Take profit percent (default 10.0)
        sl_pct:              Stop loss percent (default 5.0)
        max_hold_days:       Max holding days (default 10)
    """

    def __init__(
        self,
        min_decline_days: int = 3,
        max_decline_days: int = 5,
        min_decline_pct: float = 10.0,
        rsi_bottom: float = 20.0,
        rsi_recovery: float = 40.0,
        rsi_period: int = 14,
        tp_pct: float = 10.0,
        sl_pct: float = 5.0,
        max_hold_days: int = 10,
    ):
        self.min_decline_days = min_decline_days
        self.max_decline_days = max_decline_days
        self.min_decline_pct = min_decline_pct
        self.rsi_bottom = rsi_bottom
        self.rsi_recovery = rsi_recovery
        self.rsi_period = rsi_period
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.max_hold_days = max_hold_days

    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI series. Returns array of same length (leading NaNs)."""
        prices = np.asarray(prices, dtype=np.float64)
        n = len(prices)
        rsi = np.full(n, np.nan)
        if n < period + 1:
            return rsi

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - 100.0 / (1.0 + rs)

        for i in range(period, n - 1):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)

        return rsi

    def find_signals(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
    ) -> List[VShapeSignal]:
        """Find V-shape reversal signals.

        Scans for rapid declines followed by immediate bounce with RSI confirmation.
        """
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        rsi = self.calculate_rsi(closes, self.rsi_period)
        signals = []

        # Need enough data for RSI calculation
        start_idx = self.rsi_period + self.max_decline_days + 2
        if start_idx >= n:
            return signals

        i = start_idx
        while i < n - 1:
            # Look for rapid decline ending at or near index i
            for decline_len in range(self.min_decline_days, self.max_decline_days + 1):
                start = i - decline_len
                if start < 0:
                    continue

                peak_price = closes[start]
                bottom_price = closes[i]

                if peak_price <= 0:
                    continue

                decline_pct = (1.0 - bottom_price / peak_price) * 100.0
                if decline_pct < self.min_decline_pct:
                    continue

                # Check RSI at bottom is low enough
                rsi_bottom_val = rsi[i]
                if np.isnan(rsi_bottom_val) or rsi_bottom_val > self.rsi_bottom:
                    continue

                # Look for bounce: RSI recovers above threshold within 3 days
                for bounce_day in range(1, 4):
                    signal_idx = i + bounce_day
                    if signal_idx >= n - 1:
                        continue

                    rsi_now = rsi[signal_idx]
                    if np.isnan(rsi_now):
                        continue

                    # RSI recovered above threshold
                    if rsi_now >= self.rsi_recovery:
                        # Confirm it's a V (price is going up, no consolidation)
                        if closes[signal_idx] > closes[i]:
                            buy_idx = signal_idx + 1
                            if buy_idx >= n:
                                continue

                            buy_price = opens[buy_idx]
                            if buy_price <= 0:
                                continue

                            # Score
                            score = min(100.0,
                                min(40.0, decline_pct * 2.5) +  # Bigger V = better
                                min(30.0, (self.rsi_recovery - rsi_bottom_val) * 1.0) +  # Bigger RSI jump
                                max(0.0, (3 - bounce_day) * 10.0)  # Faster = better
                            )

                            signals.append(VShapeSignal(
                                date_idx=signal_idx,
                                decline_start_idx=start,
                                bottom_idx=i,
                                buy_price=buy_price,
                                decline_pct=round(decline_pct, 2),
                                decline_days=decline_len,
                                rsi_at_bottom=round(rsi_bottom_val, 2),
                                rsi_current=round(rsi_now, 2),
                                score=round(score, 1),
                            ))
                            i = signal_idx + 1  # Skip ahead
                            break

                if signals and signals[-1].date_idx >= i - 1:
                    break  # Found a signal, move on

            i += 1

        return signals

    def backtest(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        initial_capital: float = 1_000_000.0,
        code: str = "",
    ) -> dict:
        """Backtest V-shape reversal strategy on one stock."""
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        signals = self.find_signals(opens, highs, lows, closes, volumes, code)
        trades = []
        capital = initial_capital
        position_end = -1

        for sig in signals:
            buy_idx = sig.date_idx + 1
            if buy_idx <= position_end or buy_idx >= n:
                continue

            entry_price = sig.buy_price
            if entry_price <= 0:
                continue

            tp_price = entry_price * (1.0 + self.tp_pct / 100.0)
            sl_price = entry_price * (1.0 - self.sl_pct / 100.0)

            exit_price = None
            exit_reason = None
            exit_idx = None

            for day in range(buy_idx, min(buy_idx + self.max_hold_days, n)):
                if lows[day] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "stop_loss"
                    exit_idx = day
                    break
                if highs[day] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "take_profit"
                    exit_idx = day
                    break

            if exit_price is None:
                last_day = min(buy_idx + self.max_hold_days - 1, n - 1)
                exit_price = closes[last_day]
                exit_reason = "max_hold"
                exit_idx = last_day

            position_end = exit_idx
            return_pct = (exit_price / entry_price - 1.0) * 100.0
            capital *= (1.0 + return_pct / 100.0)

            trades.append({
                "entry_idx": buy_idx,
                "exit_idx": exit_idx,
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "return_pct": round(return_pct, 2),
                "exit_reason": exit_reason,
                "hold_days": exit_idx - buy_idx + 1,
                "decline_pct": sig.decline_pct,
                "rsi_at_bottom": sig.rsi_at_bottom,
            })

        returns = [t["return_pct"] for t in trades]
        winning = [r for r in returns if r > 0]

        return {
            "code": code,
            "trades": trades,
            "total_trades": len(trades),
            "total_return": round((capital / initial_capital - 1.0) * 100.0, 2) if trades else 0.0,
            "win_rate": round(len(winning) / len(trades) * 100.0, 2) if trades else 0.0,
            "avg_return": round(float(np.mean(returns)), 2) if returns else 0.0,
        }
