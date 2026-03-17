"""
TA-Lib Indicator Adapter for FinClaw
=====================================
Wraps TA-Lib's 150+ technical indicators as FinClaw signal generators.
Falls back to pure-Python implementations when TA-Lib is not installed.

Usage::

    from src.plugin_system.talib_adapter import TALibSignalGenerator, talib_strategy

    # Use as a signal generator
    gen = TALibSignalGenerator("rsi", period=14, overbought=70, oversold=30)
    signals = gen.generate_signals(df)

    # Quick strategy from TA-Lib indicator
    plugin = talib_strategy("macd", fast=12, slow=26, signal=9, markets=["crypto"])
    signals = plugin.generate_signals(df)
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd

from src.plugin_system.plugin_types import StrategyPlugin

logger = logging.getLogger(__name__)

try:
    import talib

    _HAS_TALIB = True
except ImportError:
    _HAS_TALIB = False
    talib = None  # type: ignore[assignment]


# ─── Pure Python fallback implementations ───────────────────────


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bbands(
    series: pd.Series, period: int = 20, nbdev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = _sma(series, period)
    std = series.rolling(period).std()
    upper = mid + nbdev * std
    lower = mid - nbdev * std
    return upper, mid, lower


def _stoch(
    high: pd.Series, low: pd.Series, close: pd.Series,
    fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    lowest = low.rolling(fastk_period).min()
    highest = high.rolling(fastk_period).max()
    fastk = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    slowk = fastk.rolling(slowk_period).mean()
    slowd = slowk.rolling(slowd_period).mean()
    return slowk, slowd


def _atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def _adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    # When plus_dm < minus_dm, plus_dm = 0 and vice versa
    mask = plus_dm < minus_dm
    plus_dm[mask] = 0
    minus_dm[~mask] = 0

    atr = _atr(high, low, close, period)
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def _cci(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    tp = (high + low + close) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma) / (0.015 * mad.replace(0, np.nan))


def _willr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    highest = high.rolling(period).max()
    lowest = low.rolling(period).min()
    return -100 * (highest - close) / (highest - lowest).replace(0, np.nan)


def _mfi(
    high: pd.Series, low: pd.Series, close: pd.Series,
    volume: pd.Series, period: int = 14,
) -> pd.Series:
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    pos_mf = raw_mf.where(tp > tp.shift(1), 0).rolling(period).sum()
    neg_mf = raw_mf.where(tp < tp.shift(1), 0).rolling(period).sum()
    mfi = 100 - 100 / (1 + pos_mf / neg_mf.replace(0, np.nan))
    return mfi


# ─── Indicator computation (TA-Lib or fallback) ────────────────

def compute_indicator(
    name: str,
    data: pd.DataFrame,
    **params: Any,
) -> dict[str, pd.Series]:
    """
    Compute a technical indicator. Uses TA-Lib if available, else pure Python.

    Returns dict of named output series.
    """
    name = name.lower()
    close = data["Close"]
    high = data.get("High", close)
    low = data.get("Low", close)
    volume = data.get("Volume", pd.Series(0, index=data.index))

    if _HAS_TALIB:
        return _compute_talib(name, close, high, low, volume, **params)
    return _compute_fallback(name, close, high, low, volume, **params)


def _compute_talib(
    name: str, close: pd.Series, high: pd.Series, low: pd.Series,
    volume: pd.Series, **params: Any,
) -> dict[str, pd.Series]:
    """Compute via TA-Lib."""
    c, h, l, v = close.values.astype(float), high.values.astype(float), low.values.astype(float), volume.values.astype(float)
    idx = close.index

    if name == "sma":
        r = talib.SMA(c, timeperiod=params.get("period", 20))
        return {"sma": pd.Series(r, index=idx)}
    elif name == "ema":
        r = talib.EMA(c, timeperiod=params.get("period", 20))
        return {"ema": pd.Series(r, index=idx)}
    elif name == "rsi":
        r = talib.RSI(c, timeperiod=params.get("period", 14))
        return {"rsi": pd.Series(r, index=idx)}
    elif name == "macd":
        m, s, hist = talib.MACD(c, fastperiod=params.get("fast", 12),
                                 slowperiod=params.get("slow", 26),
                                 signalperiod=params.get("signal", 9))
        return {"macd": pd.Series(m, index=idx), "signal": pd.Series(s, index=idx),
                "histogram": pd.Series(hist, index=idx)}
    elif name == "bbands":
        u, m, lo = talib.BBANDS(c, timeperiod=params.get("period", 20),
                                  nbdevup=params.get("nbdev", 2.0),
                                  nbdevdn=params.get("nbdev", 2.0))
        return {"upper": pd.Series(u, index=idx), "middle": pd.Series(m, index=idx),
                "lower": pd.Series(lo, index=idx)}
    elif name == "stoch":
        sk, sd = talib.STOCH(h, l, c,
                              fastk_period=params.get("fastk_period", 14),
                              slowk_period=params.get("slowk_period", 3),
                              slowd_period=params.get("slowd_period", 3))
        return {"slowk": pd.Series(sk, index=idx), "slowd": pd.Series(sd, index=idx)}
    elif name == "atr":
        r = talib.ATR(h, l, c, timeperiod=params.get("period", 14))
        return {"atr": pd.Series(r, index=idx)}
    elif name == "adx":
        r = talib.ADX(h, l, c, timeperiod=params.get("period", 14))
        return {"adx": pd.Series(r, index=idx)}
    elif name == "cci":
        r = talib.CCI(h, l, c, timeperiod=params.get("period", 14))
        return {"cci": pd.Series(r, index=idx)}
    elif name == "willr":
        r = talib.WILLR(h, l, c, timeperiod=params.get("period", 14))
        return {"willr": pd.Series(r, index=idx)}
    elif name == "mfi":
        r = talib.MFI(h, l, c, v, timeperiod=params.get("period", 14))
        return {"mfi": pd.Series(r, index=idx)}
    else:
        # Try calling TA-Lib function dynamically
        func = getattr(talib, name.upper(), None)
        if func:
            try:
                r = func(c, **{k: v for k, v in params.items()})
                if isinstance(r, tuple):
                    return {f"out{i}": pd.Series(v, index=idx) for i, v in enumerate(r)}
                return {"value": pd.Series(r, index=idx)}
            except Exception as exc:
                raise ValueError(f"TA-Lib function {name.upper()} failed: {exc}") from exc
        raise ValueError(f"Unknown indicator: {name}")


def _compute_fallback(
    name: str, close: pd.Series, high: pd.Series, low: pd.Series,
    volume: pd.Series, **params: Any,
) -> dict[str, pd.Series]:
    """Pure Python fallback."""
    if name == "sma":
        return {"sma": _sma(close, params.get("period", 20))}
    elif name == "ema":
        return {"ema": _ema(close, params.get("period", 20))}
    elif name == "rsi":
        return {"rsi": _rsi(close, params.get("period", 14))}
    elif name == "macd":
        m, s, h = _macd(close, params.get("fast", 12), params.get("slow", 26), params.get("signal", 9))
        return {"macd": m, "signal": s, "histogram": h}
    elif name == "bbands":
        u, m, lo = _bbands(close, params.get("period", 20), params.get("nbdev", 2.0))
        return {"upper": u, "middle": m, "lower": lo}
    elif name == "stoch":
        sk, sd = _stoch(high, low, close, params.get("fastk_period", 14),
                         params.get("slowk_period", 3), params.get("slowd_period", 3))
        return {"slowk": sk, "slowd": sd}
    elif name == "atr":
        return {"atr": _atr(high, low, close, params.get("period", 14))}
    elif name == "adx":
        return {"adx": _adx(high, low, close, params.get("period", 14))}
    elif name == "cci":
        return {"cci": _cci(high, low, close, params.get("period", 14))}
    elif name == "willr":
        return {"willr": _willr(high, low, close, params.get("period", 14))}
    elif name == "mfi":
        return {"mfi": _mfi(high, low, close, volume, params.get("period", 14))}
    else:
        raise ValueError(f"Unknown indicator: {name} (TA-Lib not installed for extended indicators)")


# ─── Available fallback indicators ─────────────────────────────

FALLBACK_INDICATORS = [
    "sma", "ema", "rsi", "macd", "bbands", "stoch",
    "atr", "adx", "cci", "willr", "mfi",
]


def available_indicators() -> list[str]:
    """List available indicator names."""
    if _HAS_TALIB:
        return sorted(talib.get_functions())
    return sorted(FALLBACK_INDICATORS)


# ─── TALibSignalGenerator ──────────────────────────────────────


class TALibSignalGenerator(StrategyPlugin):
    """
    Generate trading signals from a TA-Lib indicator.

    Supports common signal generation patterns:
    - Threshold-based (RSI, CCI, MFI, Williams %R)
    - Crossover-based (MACD, Stochastic, SMA/EMA crossover)
    - Band-based (Bollinger Bands)
    """

    version = "1.0.0"
    author = "FinClaw"

    def __init__(
        self,
        indicator: str = "rsi",
        name: str | None = None,
        markets: list[str] | None = None,
        risk_level: str = "medium",
        **params: Any,
    ):
        self.indicator = indicator.lower()
        self.name = name or f"talib_{self.indicator}"
        self.description = f"Signal generator based on {self.indicator.upper()}"
        self.markets = markets or ["us_stock", "crypto", "forex"]
        self.risk_level = risk_level
        self._params = params

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        result = compute_indicator(self.indicator, data, **self._params)
        return self._to_signals(result, data)

    def _to_signals(self, result: dict[str, pd.Series], data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)
        ind = self.indicator

        if ind == "rsi":
            rsi = result["rsi"]
            ob = self._params.get("overbought", 70)
            os_ = self._params.get("oversold", 30)
            signals[rsi < os_] = 1
            signals[rsi > ob] = -1

        elif ind == "macd":
            macd = result["macd"]
            sig = result["signal"]
            prev_macd = macd.shift(1)
            prev_sig = sig.shift(1)
            signals[(prev_macd <= prev_sig) & (macd > sig)] = 1
            signals[(prev_macd >= prev_sig) & (macd < sig)] = -1

        elif ind == "bbands":
            close = data["Close"]
            signals[close < result["lower"]] = 1
            signals[close > result["upper"]] = -1

        elif ind in ("sma", "ema"):
            close = data["Close"]
            ma = list(result.values())[0]
            prev_close = close.shift(1)
            prev_ma = ma.shift(1)
            signals[(prev_close <= prev_ma) & (close > ma)] = 1
            signals[(prev_close >= prev_ma) & (close < ma)] = -1

        elif ind == "stoch":
            sk = result["slowk"]
            sd = result["slowd"]
            signals[(sk < 20) & (sk > sd)] = 1
            signals[(sk > 80) & (sk < sd)] = -1

        elif ind == "cci":
            cci = result["cci"]
            signals[cci < -100] = 1
            signals[cci > 100] = -1

        elif ind == "willr":
            wr = result["willr"]
            signals[wr < -80] = 1
            signals[wr > -20] = -1

        elif ind == "mfi":
            mfi = result["mfi"]
            signals[mfi < 20] = 1
            signals[mfi > 80] = -1

        elif ind == "adx":
            adx = result["adx"]
            close = data["Close"]
            sma20 = close.rolling(20).mean()
            signals[(adx > 25) & (close > sma20)] = 1
            signals[(adx > 25) & (close < sma20)] = -1

        else:
            # Generic: if single output, use crossover with zero
            vals = list(result.values())[0]
            prev = vals.shift(1)
            signals[(prev <= 0) & (vals > 0)] = 1
            signals[(prev >= 0) & (vals < 0)] = -1

        return signals

    def get_parameters(self) -> dict[str, Any]:
        return {"indicator": self.indicator, **self._params}


def talib_strategy(
    indicator: str,
    name: str | None = None,
    **kwargs: Any,
) -> TALibSignalGenerator:
    """
    Convenience function to create a TA-Lib based strategy plugin.

    Example::

        rsi_strat = talib_strategy("rsi", period=14, overbought=75, oversold=25)
        macd_strat = talib_strategy("macd", fast=12, slow=26, signal=9)
    """
    return TALibSignalGenerator(indicator=indicator, name=name, **kwargs)
