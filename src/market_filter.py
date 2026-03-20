"""
Market Environment Filter
==========================
Determines if the broad market environment is favorable for buying.
Used as a pre-filter BEFORE cn_scanner signals.

Key insight from backtest: buying when market is trending down
leads to 56.3% first-day loss rate vs 43.8% when market is up.

Usage
-----
    from src.market_filter import MarketFilter

    mf = MarketFilter(index_prices)
    if mf.is_favorable():
        # proceed with cn_scanner buy signals
    else:
        # skip or reduce position

    score = mf.market_score()
    regime = mf.get_regime()
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


def _sma(data: Array, period: int) -> Array:
    """Simple Moving Average (internal, avoids circular imports)."""
    out = np.full_like(data, np.nan)
    if len(data) < period:
        return out
    cs = np.cumsum(data)
    out[period - 1] = cs[period - 1] / period
    out[period:] = (cs[period:] - cs[:-period]) / period
    return out


def _rsi(data: Array, period: int = 14) -> Array:
    """RSI (internal, avoids circular imports)."""
    out = np.full_like(data, np.nan)
    if len(data) < period + 1:
        return out
    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        out[period] = 100.0 - 100.0 / (1.0 + rs)
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return out


class MarketFilter:
    """Filter trading signals based on broad market conditions.

    Parameters
    ----------
    index_prices : np.ndarray, optional
        Daily close prices of a broad market index (e.g. 上证指数 sh.000001
        or 沪深300). If provided at __init__, it becomes the default for all
        subsequent method calls.
    ma_short : int
        Short moving average period (default 5).
    ma_long : int
        Long moving average period (default 20).
    """

    def __init__(
        self,
        index_prices: np.ndarray | None = None,
        ma_short: int = 5,
        ma_long: int = 20,
    ):
        self.ma_short = ma_short
        self.ma_long = ma_long
        self._default_prices: np.ndarray | None = (
            np.asarray(index_prices, dtype=np.float64)
            if index_prices is not None
            else None
        )

    # ── helpers ──────────────────────────────────────────────────

    def _resolve_prices(self, index_prices: np.ndarray | None) -> np.ndarray:
        prices = index_prices if index_prices is not None else self._default_prices
        if prices is None:
            raise ValueError("No index_prices provided and none set in __init__")
        return np.asarray(prices, dtype=np.float64)

    # ── public API ───────────────────────────────────────────────

    def is_favorable(self, index_prices: np.ndarray | None = None) -> bool:
        """Check if market environment is favorable for buying.

        Favorable triggers (ANY means favorable):
            - MA_short > MA_long  (short-term uptrend)
            - RSI(14) > 40       (not in panic territory)
            - Price > MA_long    (medium-term support intact)

        Unfavorable overrides (ANY means unfavorable, trumps favorable):
            - MA_short < MA_long AND MA_short is declining for 3+ days
              (death cross + falling)
            - RSI(14) < 25       (panic selling)
            - Price dropped > 3% in 3 trading days (crash mode)
        """
        prices = self._resolve_prices(index_prices)

        if len(prices) < self.ma_long + 3:
            # Not enough data → assume neutral/favorable
            return True

        # ── compute indicators ───────────────────────────────────
        ma_s = _sma(prices, self.ma_short)
        ma_l = _sma(prices, self.ma_long)
        rsi_arr = _rsi(prices, 14)

        latest = prices[-1]
        ma_s_val = ma_s[-1]
        ma_l_val = ma_l[-1]
        rsi_val = rsi_arr[-1]

        if np.isnan(ma_s_val) or np.isnan(ma_l_val):
            return True
        if np.isnan(rsi_val):
            rsi_val = 50.0  # fallback

        # ── unfavorable overrides (checked first) ────────────────
        # Crash mode: dropped > 3% in 3 days
        if len(prices) >= 4:
            ret_3d = (prices[-1] / prices[-4] - 1) * 100
            if ret_3d < -3.0:
                return False

        # Panic: RSI < 25
        if rsi_val < 25.0:
            return False

        # Death cross + declining MA_short for 3+ days
        if ma_s_val < ma_l_val:
            # check if MA_short is declining
            if len(ma_s) >= 4 and not np.isnan(ma_s[-4]):
                declining = all(
                    ma_s[-i - 1] <= ma_s[-i - 2]
                    for i in range(3)
                    if not np.isnan(ma_s[-i - 2])
                )
                if declining:
                    return False

        # ── favorable conditions (ANY) ───────────────────────────
        if ma_s_val > ma_l_val:
            return True
        if rsi_val > 40.0:
            return True
        if latest > ma_l_val:
            return True

        # None of the favorable conditions met
        return False

    def market_score(self, index_prices: np.ndarray | None = None) -> float:
        """Return market favorability score 0-100.

        Scoring breakdown:
            - MA trend:       0-30 points
            - RSI health:     0-25 points
            - Price vs MA20:  0-20 points
            - Momentum:       0-15 points
            - Volatility:     0-10 points

        Interpretation:
            >60  : favorable (buy normally)
            40-60: neutral (reduce position size)
            <40  : unfavorable (skip buying or very small position)
        """
        prices = self._resolve_prices(index_prices)

        if len(prices) < self.ma_long + 3:
            return 50.0  # insufficient data → neutral

        ma_s = _sma(prices, self.ma_short)
        ma_l = _sma(prices, self.ma_long)
        rsi_arr = _rsi(prices, 14)

        latest = prices[-1]
        ma_s_val = ma_s[-1]
        ma_l_val = ma_l[-1]
        rsi_val = rsi_arr[-1]

        if np.isnan(ma_s_val) or np.isnan(ma_l_val):
            return 50.0
        if np.isnan(rsi_val):
            rsi_val = 50.0

        score = 0.0

        # ── 1. MA Trend (0-30) ───────────────────────────────────
        if ma_s_val > ma_l_val:
            # Uptrend: score based on spread
            spread = (ma_s_val / ma_l_val - 1) * 100
            score += min(30.0, 15.0 + spread * 5)
        else:
            # Downtrend
            spread = (1 - ma_s_val / ma_l_val) * 100
            score += max(0.0, 15.0 - spread * 5)

        # ── 2. RSI Health (0-25) ─────────────────────────────────
        if rsi_val >= 50:
            score += min(25.0, 12.5 + (rsi_val - 50) * 0.25)
        elif rsi_val >= 30:
            score += 5.0 + (rsi_val - 30) * 0.375
        elif rsi_val >= 20:
            score += rsi_val - 20  # 0 to 10 linearly
            # Clamp: extreme oversold is bad
            score += max(0.0, min(5.0, rsi_val / 4))
        else:
            # RSI < 20 — extreme panic
            score += 0.0

        # ── 3. Price vs MA20 (0-20) ──────────────────────────────
        price_vs_ma = (latest / ma_l_val - 1) * 100
        if price_vs_ma > 0:
            score += min(20.0, 10.0 + price_vs_ma * 2)
        else:
            score += max(0.0, 10.0 + price_vs_ma * 2)

        # ── 4. Momentum (0-15) ───────────────────────────────────
        if len(prices) >= 6:
            ret_5d = (prices[-1] / prices[-6] - 1) * 100
            if ret_5d > 0:
                score += min(15.0, ret_5d * 3)
            else:
                score += max(0.0, 7.5 + ret_5d * 2.5)

        # ── 5. Volatility penalty (0-10) ─────────────────────────
        if len(prices) >= 21:
            daily_returns = np.diff(prices[-21:]) / prices[-21:-1]
            vol = np.std(daily_returns) * 100
            if vol < 1.0:
                score += 10.0
            elif vol < 2.0:
                score += 10.0 - (vol - 1.0) * 5.0
            elif vol < 3.0:
                score += 5.0 - (vol - 2.0) * 5.0
            # vol >= 3% → 0 points

        return float(np.clip(score, 0.0, 100.0))

    def get_regime(self, index_prices: np.ndarray | None = None) -> str:
        """Return market regime: 'bull', 'neutral', or 'bear'.

        Based on market_score thresholds:
            score > 60  → 'bull'
            40 ≤ score ≤ 60 → 'neutral'
            score < 40  → 'bear'
        """
        score = self.market_score(index_prices)
        if score > 60:
            return "bull"
        elif score >= 40:
            return "neutral"
        else:
            return "bear"
