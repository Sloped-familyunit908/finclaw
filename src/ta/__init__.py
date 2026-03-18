"""Technical Analysis indicators — pure Python + numpy."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]


# ── Moving Averages ──────────────────────────────────────────────────
def sma(data: Array, period: int) -> Array:
    """Simple Moving Average."""
    out = np.full_like(data, np.nan)
    cs = np.cumsum(data)
    out[period - 1:] = (cs[period - 1:] - np.concatenate(([0.0], cs[:-period]))) / period  # type: ignore[index]
    # fix: first element
    out[period - 1] = cs[period - 1] / period
    return out


def ema(data: Array, period: int) -> Array:
    """Exponential Moving Average."""
    alpha = 2.0 / (period + 1)
    out = np.empty_like(data)
    out[0] = data[0]
    for i in range(1, len(data)):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


def wma(data: Array, period: int) -> Array:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=np.float64)
    wsum = weights.sum()
    out = np.full_like(data, np.nan)
    for i in range(period - 1, len(data)):
        out[i] = np.dot(data[i - period + 1: i + 1], weights) / wsum
    return out


def dema(data: Array, period: int) -> Array:
    """Double EMA."""
    e1 = ema(data, period)
    e2 = ema(e1, period)
    return 2 * e1 - e2


def tema(data: Array, period: int) -> Array:
    """Triple EMA."""
    e1 = ema(data, period)
    e2 = ema(e1, period)
    e3 = ema(e2, period)
    return 3 * e1 - 3 * e2 + e3


# ── RSI ──────────────────────────────────────────────────────────────
def rsi(data: Array, period: int = 14) -> Array:
    """Relative Strength Index."""
    delta = np.diff(data)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = ema(gain, period)
    avg_loss = ema(loss, period)
    rs = avg_gain / np.where(avg_loss == 0, 1e-10, avg_loss)
    out = np.empty(len(data))
    out[0] = np.nan
    out[1:] = 100.0 - 100.0 / (1.0 + rs)
    return out


def stochastic_rsi(data: Array, rsi_period: int = 14, stoch_period: int = 14) -> tuple[Array, Array]:
    """Stochastic RSI → (%K, %D)."""
    r = rsi(data, rsi_period)
    k = np.full_like(r, np.nan)
    for i in range(rsi_period + stoch_period - 1, len(r)):
        window = r[i - stoch_period + 1: i + 1]
        mn, mx = np.nanmin(window), np.nanmax(window)
        k[i] = (r[i] - mn) / (mx - mn) * 100 if mx != mn else 50.0
    d = sma(k, 3)
    return k, d


# ── MACD ─────────────────────────────────────────────────────────────
def macd(data: Array, fast: int = 12, slow: int = 26, signal_period: int = 9) -> tuple[Array, Array, Array]:
    """MACD → (line, signal, histogram)."""
    line = ema(data, fast) - ema(data, slow)
    sig = ema(line, signal_period)
    hist = line - sig
    return line, sig, hist


# ── Bollinger Bands ──────────────────────────────────────────────────
def bollinger_bands(data: Array, period: int = 20, num_std: float = 2.0) -> dict[str, Array]:
    """Bollinger Bands → {upper, middle, lower, pct_b, bandwidth}."""
    mid = sma(data, period)
    std = np.full_like(data, np.nan)
    for i in range(period - 1, len(data)):
        std[i] = np.std(data[i - period + 1: i + 1], ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    band_range = upper - lower
    pct_b = np.where(band_range != 0, (data - lower) / band_range, 0.5)
    bandwidth = np.where(mid != 0, band_range / mid, 0.0)
    return {"upper": upper, "middle": mid, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth}


# ── ATR / ADX ────────────────────────────────────────────────────────
def atr(high: Array, low: Array, close: Array, period: int = 14) -> Array:
    """Average True Range."""
    tr = np.empty(len(close))
    tr[0] = high[0] - low[0]
    for i in range(1, len(close)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return ema(tr, period)


def adx(high: Array, low: Array, close: Array, period: int = 14) -> Array:
    """Average Directional Index."""
    n = len(close)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    minus_di = 100 * ema(minus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    dx = 100 * np.abs(plus_di - minus_di) / np.where(plus_di + minus_di == 0, 1e-10, plus_di + minus_di)
    return ema(dx, period)


def adx_full(high: Array, low: Array, close: Array, period: int = 14) -> tuple[Array, Array, Array]:
    """Average Directional Index with directional indicators.

    Returns
    -------
    (adx_val, plus_di, minus_di)
    """
    n = len(close)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    minus_di = 100 * ema(minus_dm, period) / np.where(atr_val == 0, 1e-10, atr_val)
    dx = 100 * np.abs(plus_di - minus_di) / np.where(plus_di + minus_di == 0, 1e-10, plus_di + minus_di)
    adx_val = ema(dx, period)
    return adx_val, plus_di, minus_di


def parabolic_sar(high: Array, low: Array, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> Array:
    """Parabolic SAR."""
    n = len(high)
    sar = np.empty(n)
    bull = True
    af = af_start
    ep = high[0]
    sar[0] = low[0]
    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if bull:
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < sar[i]:
                bull = False
                sar[i] = ep
                ep = low[i]
                af = af_start
        else:
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > sar[i]:
                bull = True
                sar[i] = ep
                ep = high[i]
                af = af_start
    return sar


# ── Volume Indicators ────────────────────────────────────────────────
def obv(close: Array, volume: Array) -> Array:
    """On-Balance Volume."""
    out = np.empty_like(close)
    out[0] = volume[0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            out[i] = out[i - 1] + volume[i]
        elif close[i] < close[i - 1]:
            out[i] = out[i - 1] - volume[i]
        else:
            out[i] = out[i - 1]
    return out


def cmf(high: Array, low: Array, close: Array, volume: Array, period: int = 20) -> Array:
    """Chaikin Money Flow."""
    mfm = np.where(high != low, ((close - low) - (high - close)) / (high - low), 0.0)
    mfv = mfm * volume
    out = np.full_like(close, np.nan)
    for i in range(period - 1, len(close)):
        vol_sum = np.sum(volume[i - period + 1: i + 1])
        out[i] = np.sum(mfv[i - period + 1: i + 1]) / vol_sum if vol_sum != 0 else 0.0
    return out


def mfi(high: Array, low: Array, close: Array, volume: Array, period: int = 14) -> Array:
    """Money Flow Index."""
    tp = (high + low + close) / 3.0
    mf = tp * volume
    out = np.full(len(close), np.nan)
    for i in range(period, len(close)):
        pos = sum(mf[j] for j in range(i - period + 1, i + 1) if tp[j] > tp[j - 1])
        neg = sum(mf[j] for j in range(i - period + 1, i + 1) if tp[j] < tp[j - 1])
        out[i] = 100.0 - 100.0 / (1.0 + pos / neg) if neg > 0 else 100.0
    return out


# ── Ichimoku Cloud ───────────────────────────────────────────────────
def ichimoku(high: Array, low: Array, close: Array,
             tenkan_period: int = 9, kijun_period: int = 26,
             senkou_b_period: int = 52, displacement: int = 26) -> dict[str, Array]:
    """Ichimoku Cloud → {tenkan, kijun, senkou_a, senkou_b, chikou}."""
    def _midline(h: Array, l: Array, period: int) -> Array:
        out = np.full(len(h), np.nan)
        for i in range(period - 1, len(h)):
            out[i] = (np.max(h[i - period + 1: i + 1]) + np.min(l[i - period + 1: i + 1])) / 2
        return out

    tenkan = _midline(high, low, tenkan_period)
    kijun = _midline(high, low, kijun_period)
    senkou_a = np.full(len(close) + displacement, np.nan)
    senkou_b = np.full(len(close) + displacement, np.nan)
    sa = (tenkan + kijun) / 2
    sb = _midline(high, low, senkou_b_period)
    senkou_a[displacement: displacement + len(sa)] = sa
    senkou_b[displacement: displacement + len(sb)] = sb
    chikou = np.full(len(close), np.nan)
    if len(close) > displacement:
        chikou[:len(close) - displacement] = close[displacement:]
    return {"tenkan": tenkan, "kijun": kijun, "senkou_a": senkou_a, "senkou_b": senkou_b, "chikou": chikou}
