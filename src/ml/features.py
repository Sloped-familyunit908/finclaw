"""
Feature engineering for ML models.

Computes technical indicators as ML features from price/volume data.
All functions operate on numpy arrays for performance.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import numpy as np


class FeatureEngine:
    """Generate ML features from OHLCV price data.

    Parameters
    ----------
    close : array-like
        Close prices.
    high : array-like, optional
        High prices (defaults to close).
    low : array-like, optional
        Low prices (defaults to close).
    volume : array-like, optional
        Volume data.
    """

    def __init__(
        self,
        close: np.ndarray,
        high: Optional[np.ndarray] = None,
        low: Optional[np.ndarray] = None,
        volume: Optional[np.ndarray] = None,
    ):
        self.close = np.asarray(close, dtype=float)
        self.high = np.asarray(high, dtype=float) if high is not None else self.close.copy()
        self.low = np.asarray(low, dtype=float) if low is not None else self.close.copy()
        self.volume = np.asarray(volume, dtype=float) if volume is not None else np.ones_like(self.close)
        self._n = len(self.close)

    # ------------------------------------------------------------------
    # Price-based features
    # ------------------------------------------------------------------

    def returns(self, period: int = 1) -> np.ndarray:
        """Simple returns over *period* days."""
        r = np.full(self._n, np.nan)
        if period < self._n:
            r[period:] = self.close[period:] / self.close[:-period] - 1.0
        return r

    def log_returns(self, period: int = 1) -> np.ndarray:
        """Log returns over *period* days."""
        r = np.full(self._n, np.nan)
        if period < self._n:
            with np.errstate(divide="ignore", invalid="ignore"):
                r[period:] = np.log(self.close[period:] / self.close[:-period])
        return r

    def rolling_volatility(self, window: int = 21) -> np.ndarray:
        """Annualised rolling volatility of daily log returns."""
        lr = self.log_returns(1)
        vol = np.full(self._n, np.nan)
        for i in range(window, self._n):
            segment = lr[i - window + 1 : i + 1]
            valid = segment[~np.isnan(segment)]
            if len(valid) >= 2:
                vol[i] = np.std(valid, ddof=1) * math.sqrt(252)
        return vol

    def multi_period_returns(self) -> Dict[str, np.ndarray]:
        """Returns for standard periods: 1d, 5d, 21d, 63d, 252d."""
        return {f"ret_{p}d": self.returns(p) for p in (1, 5, 21, 63, 252)}

    # ------------------------------------------------------------------
    # Momentum features
    # ------------------------------------------------------------------

    def rsi(self, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        delta = np.diff(self.close, prepend=np.nan)
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        avg_gain = np.full(self._n, np.nan)
        avg_loss = np.full(self._n, np.nan)
        if self._n <= period:
            return np.full(self._n, np.nan)
        avg_gain[period] = np.mean(gain[1 : period + 1])
        avg_loss[period] = np.mean(loss[1 : period + 1])
        for i in range(period + 1, self._n):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i]) / period
        rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
        result = np.full(self._n, np.nan)
        mask = ~np.isnan(rs)
        result[mask] = 100.0 - 100.0 / (1.0 + rs[mask])
        return result

    def macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD line, signal line, histogram."""
        ema_fast = self._ema(self.close, fast)
        ema_slow = self._ema(self.close, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def rate_of_change(self, period: int = 10) -> np.ndarray:
        """Rate of Change."""
        roc = np.full(self._n, np.nan)
        if period < self._n:
            roc[period:] = (self.close[period:] - self.close[:-period]) / np.where(
                self.close[:-period] == 0, 1e-10, self.close[:-period]
            ) * 100.0
        return roc

    def stochastic_oscillator(self, k_period: int = 14, d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """%K and %D of stochastic oscillator."""
        k = np.full(self._n, np.nan)
        for i in range(k_period - 1, self._n):
            h = np.max(self.high[i - k_period + 1 : i + 1])
            l = np.min(self.low[i - k_period + 1 : i + 1])
            denom = h - l
            k[i] = ((self.close[i] - l) / denom * 100.0) if denom > 0 else 50.0
        d = self._sma(k, d_period)
        return k, d

    # ------------------------------------------------------------------
    # Volume features
    # ------------------------------------------------------------------

    def obv(self) -> np.ndarray:
        """On-Balance Volume."""
        result = np.zeros(self._n)
        for i in range(1, self._n):
            if self.close[i] > self.close[i - 1]:
                result[i] = result[i - 1] + self.volume[i]
            elif self.close[i] < self.close[i - 1]:
                result[i] = result[i - 1] - self.volume[i]
            else:
                result[i] = result[i - 1]
        return result

    def vwap_ratio(self, window: int = 20) -> np.ndarray:
        """Close / rolling VWAP ratio."""
        typical = (self.high + self.low + self.close) / 3.0
        cum_tp_vol = np.cumsum(typical * self.volume)
        cum_vol = np.cumsum(self.volume)
        ratio = np.full(self._n, np.nan)
        for i in range(window - 1, self._n):
            if i >= window:
                tp_vol = cum_tp_vol[i] - cum_tp_vol[i - window]
                vol = cum_vol[i] - cum_vol[i - window]
            else:
                tp_vol = cum_tp_vol[i]
                vol = cum_vol[i]
            vwap = tp_vol / vol if vol > 0 else self.close[i]
            ratio[i] = self.close[i] / vwap if vwap > 0 else 1.0
        return ratio

    def volume_momentum(self, window: int = 20) -> np.ndarray:
        """Volume relative to its rolling mean."""
        avg = self._sma(self.volume, window)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(avg > 0, self.volume / avg, np.nan)

    # ------------------------------------------------------------------
    # Trend features
    # ------------------------------------------------------------------

    def sma_ratio(self, short: int = 20, long: int = 50) -> np.ndarray:
        """Ratio of short SMA to long SMA."""
        s = self._sma(self.close, short)
        l = self._sma(self.close, long)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(l > 0, s / l, np.nan)

    def ema_ratio(self, short: int = 12, long: int = 26) -> np.ndarray:
        """Ratio of short EMA to long EMA."""
        s = self._ema(self.close, short)
        l = self._ema(self.close, long)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(l > 0, s / l, np.nan)

    def adx(self, period: int = 14) -> np.ndarray:
        """Average Directional Index."""
        n = self._n
        if n < period + 1:
            return np.full(n, np.nan)
        up_move = np.diff(self.high, prepend=self.high[0])
        down_move = np.diff(self.low * -1, prepend=-self.low[0])  # prev_low - low
        down_move = np.concatenate([[0], self.low[:-1] - self.low[1:]])
        up_move = np.concatenate([[0], self.high[1:] - self.high[:-1]])
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr = np.zeros(n)
        for i in range(1, n):
            tr[i] = max(
                self.high[i] - self.low[i],
                abs(self.high[i] - self.close[i - 1]),
                abs(self.low[i] - self.close[i - 1]),
            )
        atr = self._ema(tr, period)
        plus_di = 100.0 * self._ema(plus_dm, period) / np.where(atr == 0, 1e-10, atr)
        minus_di = 100.0 * self._ema(minus_dm, period) / np.where(atr == 0, 1e-10, atr)
        dx = 100.0 * np.abs(plus_di - minus_di) / np.where((plus_di + minus_di) == 0, 1e-10, plus_di + minus_di)
        adx_val = self._ema(dx, period)
        return adx_val

    def bollinger_band_width(self, window: int = 20, num_std: float = 2.0) -> np.ndarray:
        """Bollinger Band width as fraction of middle band."""
        mid = self._sma(self.close, window)
        std = np.full(self._n, np.nan)
        for i in range(window - 1, self._n):
            std[i] = np.std(self.close[i - window + 1 : i + 1], ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(mid > 0, 2 * num_std * std / mid, np.nan)

    def distance_from_52w(self) -> Tuple[np.ndarray, np.ndarray]:
        """Distance from 52-week (252-day) high and low as fractions."""
        window = min(252, self._n)
        high_dist = np.full(self._n, np.nan)
        low_dist = np.full(self._n, np.nan)
        for i in range(window - 1, self._n):
            h = np.max(self.high[i - window + 1 : i + 1])
            l = np.min(self.low[i - window + 1 : i + 1])
            high_dist[i] = (self.close[i] - h) / h if h > 0 else 0.0
            low_dist[i] = (self.close[i] - l) / l if l > 0 else 0.0
        return high_dist, low_dist

    # ------------------------------------------------------------------
    # Cross-sectional features
    # ------------------------------------------------------------------

    @staticmethod
    def cross_sectional_zscore(feature_matrix: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Z-score normalize each feature across a universe (cross-sectionally).

        Parameters
        ----------
        feature_matrix : dict
            {ticker: feature_array} where all arrays have the same length.

        Returns
        -------
        dict
            {ticker: z_scored_array}
        """
        tickers = list(feature_matrix.keys())
        if not tickers:
            return {}
        n = len(feature_matrix[tickers[0]])
        result = {t: np.full(n, np.nan) for t in tickers}
        for i in range(n):
            vals = []
            valid_tickers = []
            for t in tickers:
                v = feature_matrix[t][i]
                if not np.isnan(v):
                    vals.append(v)
                    valid_tickers.append(t)
            if len(vals) >= 2:
                mean = np.mean(vals)
                std = np.std(vals, ddof=1)
                if std > 0:
                    for t, v in zip(valid_tickers, vals):
                        result[t][i] = (v - mean) / std
        return result

    # ------------------------------------------------------------------
    # Generate all features
    # ------------------------------------------------------------------

    def generate_all(self) -> Dict[str, np.ndarray]:
        """Generate all available features as a dictionary."""
        features: Dict[str, np.ndarray] = {}

        # Price-based
        features.update(self.multi_period_returns())
        features["log_ret_1d"] = self.log_returns(1)
        features["volatility_21d"] = self.rolling_volatility(21)

        # Momentum
        features["rsi_14"] = self.rsi(14)
        macd_line, signal_line, histogram = self.macd()
        features["macd"] = macd_line
        features["macd_signal"] = signal_line
        features["macd_histogram"] = histogram
        features["roc_10"] = self.rate_of_change(10)
        k, d = self.stochastic_oscillator()
        features["stoch_k"] = k
        features["stoch_d"] = d

        # Volume
        features["obv"] = self.obv()
        features["vwap_ratio"] = self.vwap_ratio()
        features["volume_momentum"] = self.volume_momentum()

        # Trend
        features["sma_20_50_ratio"] = self.sma_ratio(20, 50)
        features["ema_12_26_ratio"] = self.ema_ratio(12, 26)
        features["adx_14"] = self.adx(14)
        features["bb_width"] = self.bollinger_band_width()
        high_dist, low_dist = self.distance_from_52w()
        features["dist_52w_high"] = high_dist
        features["dist_52w_low"] = low_dist

        return features

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Exponential moving average."""
        result = np.full(len(data), np.nan)
        alpha = 2.0 / (period + 1)
        start = None
        for i in range(len(data)):
            if not np.isnan(data[i]):
                if start is None:
                    result[i] = data[i]
                    start = i
                else:
                    result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    def _sma(self, data: np.ndarray, period: int) -> np.ndarray:
        """Simple moving average."""
        result = np.full(len(data), np.nan)
        cumsum = np.nancumsum(data)
        for i in range(period - 1, len(data)):
            if i >= period:
                result[i] = (cumsum[i] - cumsum[i - period]) / period
            else:
                result[i] = cumsum[i] / period
        return result
