"""
涨停回调不破底 - Short-term Dragon Head Strategy
============================================
A-share classic: buy after limit-up day pullback without breaking the bottom.

Strategy:
  1. Detect limit-up day (close/prev_close >= 1.095 for main board, >= 1.195 for 科创/创业)
  2. Wait 2-4 days of pullback
  3. Confirm pullback doesn't break limit-up day's LOW
  4. Volume shrinks during pullback (< 60% of limit-up day volume)
  5. Buy at T+1 open after confirmation
  6. Sell: +10% take profit, -5% stop loss, or 5 days max hold

Board classification:
  - Main board: 600/601/603/000/001/002 → 10% limit
  - ChiNext (创业板): 300/301 → 20% limit
  - STAR Market (科创板): 688 → 20% limit

This strategy runs PARALLEL to existing strategies — no existing code is modified.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LimitUpSignal:
    """A confirmed pullback-after-limit-up buy signal."""
    date_idx: int        # Index of the signal day (last pullback day)
    limit_up_idx: int    # Index of the limit-up day
    buy_price: float     # T+1 open price (next day after signal)
    limit_up_low: float  # Bottom of the limit-up candle
    limit_up_volume: float  # Volume on limit-up day
    pullback_days: int   # How many days of pullback
    volume_ratio: float  # Average pullback volume / limit-up volume
    score: float         # Signal quality score 0-100


class LimitUpPullback:
    """涨停回调不破底 strategy implementation.

    Parameters:
        tp_pct:             Take profit percentage (default 10.0)
        sl_pct:             Stop loss percentage (default 5.0)
        max_hold_days:      Maximum holding period in trading days (default 5)
        min_pullback_days:  Minimum pullback days after limit-up (default 2)
        max_pullback_days:  Maximum pullback days to still consider (default 4)
        max_volume_ratio:   Max average pullback volume / limit-up volume (default 0.6)
    """

    def __init__(
        self,
        tp_pct: float = 10.0,
        sl_pct: float = 5.0,
        max_hold_days: int = 5,
        min_pullback_days: int = 2,
        max_pullback_days: int = 4,
        max_volume_ratio: float = 0.6,
    ):
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.max_hold_days = max_hold_days
        self.min_pullback_days = min_pullback_days
        self.max_pullback_days = max_pullback_days
        self.max_volume_ratio = max_volume_ratio

    # ─── board type helpers ─────────────────────────────────

    @staticmethod
    def get_limit_pct(code: str) -> float:
        """Return the daily limit percentage for a stock code.

        Returns 0.20 for 科创板 (688) and 创业板 (300/301),
        0.10 for main board (600/601/603/000/001/002).
        Falls back to 0.10 for unknown prefixes.
        """
        # Strip exchange prefix: "sh.600000" -> "600000", "sz.300001" -> "300001"
        pure = code.replace("sh.", "").replace("sz.", "").replace("SH.", "").replace("SZ.", "")
        if pure.startswith("688"):
            return 0.20  # STAR Market (科创板)
        if pure.startswith("300") or pure.startswith("301"):
            return 0.20  # ChiNext (创业板)
        return 0.10  # Main board

    @staticmethod
    def is_st(code: str) -> bool:
        """Heuristic: ST stocks have 5% limit. We skip them."""
        # Caller should check stock name for "ST" — here we just provide the helper.
        return False  # Actual ST detection is done by caller via stock name

    # ─── core detection ─────────────────────────────────────

    def detect_limit_up(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
    ) -> List[int]:
        """Find all limit-up day indices in the price history.

        A day is limit-up if close/prev_close >= (1 + limit_pct * 0.95).
        We use 0.95 multiplier to handle rounding (9.5% for 10% board, 19% for 20% board).

        Returns:
            List of indices where limit-up occurred.
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        if n < 2:
            return []

        limit_pct = self.get_limit_pct(code)
        threshold = 1.0 + limit_pct * 0.95  # 1.095 for 10%, 1.19 for 20%

        limit_up_days = []
        for i in range(1, n):
            if closes[i - 1] > 0:
                change = closes[i] / closes[i - 1]
                if change >= threshold:
                    limit_up_days.append(i)

        return limit_up_days

    def find_pullback_signals(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
    ) -> List[LimitUpSignal]:
        """Find valid pullback-after-limit-up patterns.

        For each limit-up day, check if the subsequent days form a valid pullback:
          1. Pullback lasts min_pullback_days to max_pullback_days
          2. No day's low breaks below the limit-up day's low
          3. Average volume during pullback < max_volume_ratio * limit-up volume
          4. There must be a T+1 day after the signal to buy on

        Returns:
            List of LimitUpSignal for valid signals.
        """
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        limit_up_days = self.detect_limit_up(opens, highs, lows, closes, volumes, code)
        signals = []

        for lu_idx in limit_up_days:
            lu_low = lows[lu_idx]
            lu_volume = volumes[lu_idx]

            if lu_volume <= 0:
                continue

            # Try each pullback length
            for pb_days in range(self.min_pullback_days, self.max_pullback_days + 1):
                signal_idx = lu_idx + pb_days  # Last day of pullback
                buy_idx = signal_idx + 1       # T+1 buy day

                if buy_idx >= n:
                    continue  # Not enough data for T+1 buy

                # Check pullback validity
                pullback_slice = slice(lu_idx + 1, signal_idx + 1)
                pullback_lows = lows[pullback_slice]
                pullback_volumes = volumes[pullback_slice]

                if len(pullback_lows) != pb_days:
                    continue

                # Condition 1: No day's low breaks limit-up day's low
                if np.any(pullback_lows < lu_low):
                    continue

                # Condition 2: Volume shrinkage
                avg_pb_volume = np.mean(pullback_volumes)
                vol_ratio = avg_pb_volume / lu_volume
                if vol_ratio > self.max_volume_ratio:
                    continue

                # Condition 3: Pullback should actually be pulling back
                # (close of last pullback day < close of limit-up day)
                if closes[signal_idx] >= closes[lu_idx]:
                    continue  # Not really pulling back

                # Score calculation (0-100)
                score = self._calculate_score(vol_ratio, pb_days, closes, lu_idx, signal_idx)

                buy_price = opens[buy_idx]
                if buy_price <= 0:
                    continue

                signals.append(LimitUpSignal(
                    date_idx=signal_idx,
                    limit_up_idx=lu_idx,
                    buy_price=buy_price,
                    limit_up_low=lu_low,
                    limit_up_volume=lu_volume,
                    pullback_days=pb_days,
                    volume_ratio=vol_ratio,
                    score=score,
                ))

                # Found a valid signal for this limit-up, don't check longer pullbacks
                break

        return signals

    def _calculate_score(
        self,
        vol_ratio: float,
        pb_days: int,
        closes: np.ndarray,
        lu_idx: int,
        signal_idx: int,
    ) -> float:
        """Calculate signal quality score (0-100).

        Higher score = better signal:
          - Lower volume ratio = more exhaustion = better
          - 2-3 day pullback preferred over 4 days
          - Smaller pullback % = stronger support
        """
        # Volume factor: 0.6 → 40pts, 0.3 → 60pts, 0.1 → 80pts (capped at 80)
        vol_score = min(80.0, max(0.0, (0.7 - vol_ratio) * 100.0))

        # Days factor: 2-3 days are ideal
        if pb_days <= 3:
            days_score = 15.0
        else:
            days_score = 5.0

        # Pullback depth: smaller pullback = stronger
        pullback_pct = 1.0 - closes[signal_idx] / closes[lu_idx]
        depth_score = max(0.0, min(5.0, (0.10 - pullback_pct) * 50.0))

        return min(100.0, vol_score + days_score + depth_score)

    # ─── backtest ───────────────────────────────────────────

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
        """Backtest the strategy on one stock.

        Buy at T+1 OPEN price after signal confirmation.
        Sell when:
          - High reaches entry * (1 + tp_pct/100) → take profit
          - Low reaches entry * (1 - sl_pct/100) → stop loss
          - Hold exceeds max_hold_days → time exit

        Returns dict with:
          trades, total_return, win_rate, avg_return, max_return, min_return, avg_hold_days
        """
        opens = np.asarray(opens, dtype=np.float64)
        highs = np.asarray(highs, dtype=np.float64)
        lows = np.asarray(lows, dtype=np.float64)
        closes = np.asarray(closes, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(closes)

        signals = self.find_pullback_signals(opens, highs, lows, closes, volumes, code)
        trades = []
        capital = initial_capital
        position_end = -1  # Index of the last day a position was held

        for sig in signals:
            buy_idx = sig.date_idx + 1  # T+1 open

            # Skip if we're still in a position
            if buy_idx <= position_end:
                continue

            entry_price = sig.buy_price
            if entry_price <= 0:
                continue

            tp_price = entry_price * (1.0 + self.tp_pct / 100.0)
            sl_price = entry_price * (1.0 - self.sl_pct / 100.0)

            # Simulate holding
            exit_price = None
            exit_reason = None
            exit_idx = None
            hold_days = 0

            for day in range(buy_idx, min(buy_idx + self.max_hold_days, n)):
                hold_days += 1

                # Check stop loss first (assume worst case: SL hit before TP on same day)
                if lows[day] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "stop_loss"
                    exit_idx = day
                    break

                # Check take profit
                if highs[day] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "take_profit"
                    exit_idx = day
                    break

            # Time exit: sell at close of last hold day
            if exit_price is None:
                last_day = min(buy_idx + self.max_hold_days - 1, n - 1)
                exit_price = closes[last_day]
                exit_reason = "max_hold"
                exit_idx = last_day
                hold_days = last_day - buy_idx + 1

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
                "hold_days": hold_days,
                "pullback_days": sig.pullback_days,
                "volume_ratio": round(sig.volume_ratio, 4),
                "score": round(sig.score, 1),
            })

        # Summary
        returns = [t["return_pct"] for t in trades]
        winning = [r for r in returns if r > 0]

        return {
            "code": code,
            "trades": trades,
            "total_trades": len(trades),
            "total_return": round((capital / initial_capital - 1.0) * 100.0, 2) if trades else 0.0,
            "win_rate": round(len(winning) / len(trades) * 100.0, 2) if trades else 0.0,
            "avg_return": round(float(np.mean(returns)), 2) if returns else 0.0,
            "max_return": round(float(np.max(returns)), 2) if returns else 0.0,
            "min_return": round(float(np.min(returns)), 2) if returns else 0.0,
            "avg_hold_days": round(float(np.mean([t["hold_days"] for t in trades])), 1) if trades else 0.0,
        }
