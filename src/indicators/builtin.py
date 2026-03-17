"""
Pure-Python technical indicators — zero external dependencies.

Each function takes a list of OHLCV candles (dicts with keys:
``open``, ``high``, ``low``, ``close``, ``volume``) or plain
numeric lists where noted, and returns computed values as a list.

Candle dict example::

    {"open": 100.0, "high": 105.0, "low": 99.0, "close": 103.0, "volume": 12000}
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

Candle = Dict[str, float]

# ── helpers ──────────────────────────────────────────────────────────

def _closes(candles: Sequence[Candle]) -> List[float]:
    return [c["close"] for c in candles]


def _highs(candles: Sequence[Candle]) -> List[float]:
    return [c["high"] for c in candles]


def _lows(candles: Sequence[Candle]) -> List[float]:
    return [c["low"] for c in candles]


def _volumes(candles: Sequence[Candle]) -> List[float]:
    return [c["volume"] for c in candles]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _std(values: Sequence[float], ddof: int = 0) -> float:
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - ddof))


# ── Moving Averages ──────────────────────────────────────────────────

def sma(prices: List[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average.

    Formula: SMA(t) = sum(price[t-period+1..t]) / period

    Returns a list of same length as *prices*; first ``period-1`` values
    are ``None``.
    """
    out: List[Optional[float]] = [None] * len(prices)
    if len(prices) < period:
        return out
    window_sum = sum(prices[:period])
    out[period - 1] = window_sum / period
    for i in range(period, len(prices)):
        window_sum += prices[i] - prices[i - period]
        out[i] = window_sum / period
    return out


def ema(prices: List[float], period: int) -> List[float]:
    """Exponential Moving Average.

    Formula: EMA(t) = α * price(t) + (1-α) * EMA(t-1),  α = 2/(period+1)
    Seed: EMA(0) = price(0).
    """
    alpha = 2.0 / (period + 1)
    out = [prices[0]]
    for i in range(1, len(prices)):
        out.append(alpha * prices[i] + (1 - alpha) * out[-1])
    return out


# ── 1. RSI ───────────────────────────────────────────────────────────

def rsi(candles: Sequence[Candle], period: int = 14) -> List[Optional[float]]:
    """Relative Strength Index (Wilder's smoothed).

    Formula:
        change  = close(t) - close(t-1)
        gain    = max(change, 0)
        loss    = max(-change, 0)
        avg_gain = EMA(gain, period)   (Wilder smoothing)
        avg_loss = EMA(loss, period)
        RS      = avg_gain / avg_loss
        RSI     = 100 - 100 / (1 + RS)

    Returns list of ``len(candles)`` values; first value is ``None``.
    """
    closes = _closes(candles)
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n < 2:
        return out

    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, n)]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, n)]

    if len(gains) < period:
        return out

    avg_gain = _mean(gains[:period])
    avg_loss = _mean(losses[:period])

    for i in range(period, len(gains) + 1):
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)
        if i < len(gains):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    return out


# ── 2. MACD ──────────────────────────────────────────────────────────

def macd(
    candles: Sequence[Candle],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Dict[str, List[float]]:
    """Moving Average Convergence Divergence.

    Formula:
        MACD line  = EMA(close, fast) - EMA(close, slow)
        Signal     = EMA(MACD line, signal_period)
        Histogram  = MACD line - Signal

    Returns dict with keys ``macd``, ``signal``, ``histogram``.
    """
    closes = _closes(candles)
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_line = ema(macd_line, signal_period)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


# ── 3. Bollinger Bands ──────────────────────────────────────────────

def bollinger_bands(
    candles: Sequence[Candle],
    period: int = 20,
    num_std: float = 2.0,
) -> Dict[str, List[Optional[float]]]:
    """Bollinger Bands.

    Formula:
        Middle = SMA(close, period)
        Upper  = Middle + num_std * σ(close, period)
        Lower  = Middle - num_std * σ(close, period)
        %B     = (close - Lower) / (Upper - Lower)
        BW     = (Upper - Lower) / Middle

    Returns dict with ``upper``, ``middle``, ``lower``, ``pct_b``, ``bandwidth``.
    """
    closes = _closes(candles)
    mid = sma(closes, period)
    n = len(closes)
    upper: List[Optional[float]] = [None] * n
    lower: List[Optional[float]] = [None] * n
    pct_b: List[Optional[float]] = [None] * n
    bandwidth: List[Optional[float]] = [None] * n

    for i in range(period - 1, n):
        window = closes[i - period + 1: i + 1]
        sd = _std(window)
        m = mid[i]
        assert m is not None
        upper[i] = m + num_std * sd
        lower[i] = m - num_std * sd
        rng = upper[i] - lower[i]  # type: ignore
        pct_b[i] = (closes[i] - lower[i]) / rng if rng else 0.5  # type: ignore
        bandwidth[i] = rng / m if m else 0.0  # type: ignore

    return {"upper": upper, "middle": mid, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth}


# ── 4. ATR ───────────────────────────────────────────────────────────

def atr(candles: Sequence[Candle], period: int = 14) -> List[Optional[float]]:
    """Average True Range.

    Formula:
        TR(t) = max(high-low, |high-prev_close|, |low-prev_close|)
        ATR   = Wilder-smoothed average of TR over *period*.

    Returns list; first value is ``None``.
    """
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    n = len(candles)
    tr = [highs[0] - lows[0]]
    for i in range(1, n):
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    out: List[Optional[float]] = [None] * n
    if n < period:
        return out
    atr_val = _mean(tr[:period])
    out[period - 1] = atr_val
    for i in range(period, n):
        atr_val = (atr_val * (period - 1) + tr[i]) / period
        out[i] = atr_val
    return out


# ── 5. Stochastic Oscillator ────────────────────────────────────────

def stochastic_oscillator(
    candles: Sequence[Candle],
    k_period: int = 14,
    d_period: int = 3,
) -> Dict[str, List[Optional[float]]]:
    """Stochastic Oscillator.

    Formula:
        %K = (close - lowest_low(k_period)) / (highest_high(k_period) - lowest_low(k_period)) * 100
        %D = SMA(%K, d_period)

    Returns dict with ``k`` and ``d``.
    """
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    n = len(candles)
    k: List[Optional[float]] = [None] * n

    for i in range(k_period - 1, n):
        hh = max(highs[i - k_period + 1: i + 1])
        ll = min(lows[i - k_period + 1: i + 1])
        k[i] = (closes[i] - ll) / (hh - ll) * 100.0 if hh != ll else 50.0

    # %D = SMA of %K (only over non-None values)
    k_vals = [v if v is not None else 0.0 for v in k]
    d_raw = sma(k_vals, d_period)
    d: List[Optional[float]] = [None] * n
    start = k_period - 1 + d_period - 1
    for i in range(start, n):
        d[i] = d_raw[i]

    return {"k": k, "d": d}


# ── 6. VWAP ─────────────────────────────────────────────────────────

def vwap(candles: Sequence[Candle]) -> List[float]:
    """Volume Weighted Average Price.

    Formula:
        Typical Price = (high + low + close) / 3
        VWAP(t) = Σ(TP * volume) / Σ(volume)  cumulative from start.

    Typically reset per trading day; here computed cumulatively over
    the provided candles.
    """
    cum_tp_vol = 0.0
    cum_vol = 0.0
    out: List[float] = []
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        cum_tp_vol += tp * c["volume"]
        cum_vol += c["volume"]
        out.append(cum_tp_vol / cum_vol if cum_vol else 0.0)
    return out


# ── 7. OBV ───────────────────────────────────────────────────────────

def obv(candles: Sequence[Candle]) -> List[float]:
    """On-Balance Volume.

    Formula:
        if close > prev_close: OBV += volume
        if close < prev_close: OBV -= volume
        else: OBV unchanged
    """
    closes = _closes(candles)
    volumes = _volumes(candles)
    out = [volumes[0]]
    for i in range(1, len(candles)):
        if closes[i] > closes[i - 1]:
            out.append(out[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            out.append(out[-1] - volumes[i])
        else:
            out.append(out[-1])
    return out


# ── 8. Ichimoku Cloud ───────────────────────────────────────────────

def ichimoku(
    candles: Sequence[Candle],
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52,
    displacement: int = 26,
) -> Dict[str, List[Optional[float]]]:
    """Ichimoku Cloud.

    Components:
        Tenkan-sen  = (highest_high + lowest_low) / 2  over tenkan_period
        Kijun-sen   = same over kijun_period
        Senkou A    = (Tenkan + Kijun) / 2, displaced forward
        Senkou B    = midline over senkou_b_period, displaced forward
        Chikou      = close displaced backward
    """
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    n = len(candles)

    def _midline(period: int) -> List[Optional[float]]:
        out: List[Optional[float]] = [None] * n
        for i in range(period - 1, n):
            out[i] = (max(highs[i - period + 1: i + 1]) + min(lows[i - period + 1: i + 1])) / 2
        return out

    tenkan = _midline(tenkan_period)
    kijun = _midline(kijun_period)

    # Senkou A & B displaced forward
    total = n + displacement
    senkou_a: List[Optional[float]] = [None] * total
    senkou_b_line = _midline(senkou_b_period)
    senkou_b: List[Optional[float]] = [None] * total

    for i in range(n):
        if tenkan[i] is not None and kijun[i] is not None:
            senkou_a[i + displacement] = (tenkan[i] + kijun[i]) / 2  # type: ignore
        if senkou_b_line[i] is not None:
            senkou_b[i + displacement] = senkou_b_line[i]

    # Chikou = close displaced backward
    chikou: List[Optional[float]] = [None] * n
    for i in range(n - displacement):
        chikou[i] = closes[i + displacement]

    return {
        "tenkan": tenkan,
        "kijun": kijun,
        "senkou_a": senkou_a,
        "senkou_b": senkou_b,
        "chikou": chikou,
    }


# ── 9. Fibonacci Retracement ────────────────────────────────────────

def fibonacci_retracement(
    candles: Sequence[Candle],
    lookback: Optional[int] = None,
) -> Dict[str, float]:
    """Fibonacci Retracement levels — auto-detect swing high/low.

    Uses the highest high and lowest low over the given candles
    (or last *lookback* candles) then computes standard Fibonacci
    retracement levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%.

    Returns dict with keys ``swing_high``, ``swing_low``, and each
    level as string key (e.g. ``"23.6%"``).
    """
    subset = candles if lookback is None else candles[-lookback:]
    highs = _highs(subset)
    lows = _lows(subset)
    swing_high = max(highs)
    swing_low = min(lows)
    diff = swing_high - swing_low
    levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    result: Dict[str, float] = {"swing_high": swing_high, "swing_low": swing_low}
    for lvl in levels:
        key = f"{lvl*100:.1f}%"
        result[key] = swing_high - diff * lvl
    return result


# ── 10. Supertrend ───────────────────────────────────────────────────

def supertrend(
    candles: Sequence[Candle],
    period: int = 10,
    multiplier: float = 3.0,
) -> Dict[str, List[Optional[float]]]:
    """Supertrend — ATR-based trend indicator.

    Formula:
        HL2       = (high + low) / 2
        BasicUp   = HL2 - multiplier * ATR
        BasicDn   = HL2 + multiplier * ATR
        FinalUp   = max(BasicUp, prev FinalUp) if prev close > prev FinalUp else BasicUp
        FinalDn   = min(BasicDn, prev FinalDn) if prev close < prev FinalDn else BasicDn
        Supertrend = FinalDn if uptrend else FinalUp

    Returns dict with ``supertrend`` (values), ``direction`` (1=up, -1=down).
    """
    atr_vals = atr(candles, period)
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    n = len(candles)

    st: List[Optional[float]] = [None] * n
    direction: List[Optional[float]] = [None] * n

    if n < period:
        return {"supertrend": st, "direction": direction}

    final_up = [0.0] * n
    final_dn = [0.0] * n

    start = period - 1
    for i in range(start, n):
        hl2 = (highs[i] + lows[i]) / 2.0
        a = atr_vals[i] if atr_vals[i] is not None else 0.0
        basic_up = hl2 - multiplier * a
        basic_dn = hl2 + multiplier * a

        if i == start:
            final_up[i] = basic_up
            final_dn[i] = basic_dn
            direction[i] = 1 if closes[i] > basic_dn else -1  # type: ignore
        else:
            final_up[i] = max(basic_up, final_up[i - 1]) if closes[i - 1] > final_up[i - 1] else basic_up
            final_dn[i] = min(basic_dn, final_dn[i - 1]) if closes[i - 1] < final_dn[i - 1] else basic_dn

            if direction[i - 1] == 1:  # type: ignore
                direction[i] = -1 if closes[i] < final_up[i] else 1  # type: ignore
            else:
                direction[i] = 1 if closes[i] > final_dn[i] else -1  # type: ignore

        st[i] = final_up[i] if direction[i] == 1 else final_dn[i]

    return {"supertrend": st, "direction": direction}
