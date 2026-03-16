"""
Feature Store — Compute, cache, and serve ML features for financial tickers.

Provides a registry of named feature computation functions, on-disk caching,
and batch feature matrix generation for cross-sectional ML models.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np


class FeatureStore:
    """Centralized feature computation and caching.

    Parameters
    ----------
    cache_dir : str
        Directory for cached feature files. Set to ``None`` to disable caching.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        if cache_dir:
            self.cache_dir = Path(os.path.expanduser(cache_dir))
        else:
            self.cache_dir = None
        self._registry: Dict[str, Callable] = {}
        self._register_builtins()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_feature(self, name: str, compute_fn: Callable) -> None:
        """Register a custom feature computation function.

        Parameters
        ----------
        name : str
            Unique feature name.
        compute_fn : callable
            ``fn(prices: list[float]) -> float | list[float]``
        """
        self._registry[name] = compute_fn

    def list_features(self) -> List[str]:
        """Return sorted list of registered feature names."""
        return sorted(self._registry.keys())

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------

    def compute(self, ticker: str, features: List[str], prices: Optional[List[float]] = None) -> Dict[str, Any]:
        """Compute requested features for a ticker.

        Parameters
        ----------
        ticker : str
        features : list of feature names
        prices : list[float], optional
            Price series. Required for actual computation; if cached, can be omitted.

        Returns
        -------
        dict : feature_name → value(s)
        """
        # Try cache first
        cached = self._load_cache(ticker, features)
        if cached is not None:
            return cached

        if prices is None:
            raise ValueError(f"prices required to compute features for {ticker} (no cache hit)")

        result: Dict[str, Any] = {}
        for feat in features:
            fn = self._registry.get(feat)
            if fn is None:
                raise KeyError(f"Unknown feature '{feat}'. Available: {self.list_features()}")
            result[feat] = fn(prices)

        self._save_cache(ticker, features, result)
        return result

    def get_feature_matrix(
        self,
        tickers: List[str],
        features: List[str],
        price_data: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Compute feature matrix for multiple tickers.

        Parameters
        ----------
        tickers : list of ticker symbols
        features : list of feature names
        price_data : dict, optional
            ``{ticker: prices_list}``. Required if not cached.

        Returns
        -------
        dict : ``{ticker: {feature: value}}``
        """
        matrix: Dict[str, Dict[str, Any]] = {}
        for ticker in tickers:
            prices = price_data.get(ticker) if price_data else None
            matrix[ticker] = self.compute(ticker, features, prices)
        return matrix

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------

    def _cache_key(self, ticker: str, features: List[str]) -> str:
        key_str = f"{ticker}:{','.join(sorted(features))}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_cache(self, ticker: str, features: List[str]) -> Optional[Dict[str, Any]]:
        if self.cache_dir is None:
            return None
        path = self.cache_dir / f"{self._cache_key(ticker, features)}.json"
        if not path.exists():
            return None
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # Verify all features present
            if all(feat in data for feat in features):
                return data
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def _save_cache(self, ticker: str, features: List[str], data: Dict[str, Any]) -> None:
        if self.cache_dir is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.cache_dir / f"{self._cache_key(ticker, features)}.json"
        # Convert numpy types to JSON-serializable
        serializable = {}
        for k, v in data.items():
            if isinstance(v, np.ndarray):
                serializable[k] = v.tolist()
            elif isinstance(v, (np.floating, np.integer)):
                serializable[k] = float(v)
            else:
                serializable[k] = v
        try:
            with open(path, 'w') as f:
                json.dump(serializable, f)
        except OSError:
            pass

    def clear_cache(self, ticker: Optional[str] = None) -> int:
        """Clear cached features. Returns count of files removed."""
        if self.cache_dir is None or not self.cache_dir.exists():
            return 0
        count = 0
        for p in self.cache_dir.glob("*.json"):
            p.unlink()
            count += 1
        return count

    # ------------------------------------------------------------------
    # Built-in features
    # ------------------------------------------------------------------

    def _register_builtins(self) -> None:
        """Register built-in feature computation functions."""
        self.register_feature('returns', _feat_returns)
        self.register_feature('volatility', _feat_volatility)
        self.register_feature('rsi', _feat_rsi)
        self.register_feature('macd', _feat_macd)
        self.register_feature('volume_ratio', _feat_volume_ratio)
        self.register_feature('price_momentum', _feat_price_momentum)
        self.register_feature('log_returns', _feat_log_returns)
        self.register_feature('sma_ratio', _feat_sma_ratio)
        self.register_feature('drawdown', _feat_drawdown)
        self.register_feature('skewness', _feat_skewness)


# ======================================================================
# Built-in feature functions
# ======================================================================

def _feat_returns(prices: List[float]) -> float:
    """Latest 1-day return."""
    if len(prices) < 2:
        return 0.0
    return (prices[-1] / prices[-2]) - 1 if prices[-2] != 0 else 0.0


def _feat_log_returns(prices: List[float]) -> float:
    """Latest 1-day log return."""
    if len(prices) < 2 or prices[-2] <= 0 or prices[-1] <= 0:
        return 0.0
    return math.log(prices[-1] / prices[-2])


def _feat_volatility(prices: List[float], window: int = 21) -> float:
    """Annualised volatility over the last *window* bars."""
    if len(prices) < window + 1:
        return 0.0
    rets = [(prices[i] / prices[i - 1]) - 1 for i in range(-window, 0)]
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / max(len(rets) - 1, 1)
    return math.sqrt(var) * math.sqrt(252)


def _feat_rsi(prices: List[float], period: int = 14) -> float:
    """RSI (Wilder's smoothing) at latest bar."""
    if len(prices) < period + 2:
        return 50.0
    gains, losses = [], []
    for i in range(-period - 1, 0):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _feat_macd(prices: List[float]) -> float:
    """MACD histogram value at latest bar."""
    if len(prices) < 35:
        return 0.0
    ema12 = _ema(prices, 12)
    ema26 = _ema(prices, 26)
    macd_line = ema12 - ema26
    # Signal is EMA(9) of macd_line... approximate with last value
    return macd_line


def _feat_volume_ratio(prices: List[float], window: int = 20) -> float:
    """Placeholder — returns 1.0 (volume data not in price-only input)."""
    return 1.0


def _feat_price_momentum(prices: List[float], period: int = 21) -> float:
    """Price momentum: return over *period* bars."""
    if len(prices) < period + 1:
        return 0.0
    return (prices[-1] / prices[-period - 1]) - 1 if prices[-period - 1] != 0 else 0.0


def _feat_sma_ratio(prices: List[float], short: int = 20, long: int = 50) -> float:
    """Ratio of short SMA to long SMA."""
    if len(prices) < long:
        return 1.0
    sma_short = sum(prices[-short:]) / short
    sma_long = sum(prices[-long:]) / long
    return sma_short / sma_long if sma_long > 0 else 1.0


def _feat_drawdown(prices: List[float]) -> float:
    """Current drawdown from peak."""
    if not prices:
        return 0.0
    peak = max(prices)
    return (prices[-1] - peak) / peak if peak > 0 else 0.0


def _feat_skewness(prices: List[float], window: int = 63) -> float:
    """Skewness of returns over last *window* bars."""
    if len(prices) < window + 1:
        return 0.0
    rets = [(prices[i] / prices[i - 1]) - 1 for i in range(-window, 0)]
    n = len(rets)
    mean = sum(rets) / n
    m2 = sum((r - mean) ** 2 for r in rets) / n
    m3 = sum((r - mean) ** 3 for r in rets) / n
    if m2 == 0:
        return 0.0
    return m3 / (m2 ** 1.5)


def _ema(prices: List[float], period: int) -> float:
    """EMA at the latest bar."""
    alpha = 2.0 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = alpha * p + (1 - alpha) * ema
    return ema
