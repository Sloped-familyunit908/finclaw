"""Tests for src.indicators.builtin and src.indicators.signals — zero-dependency indicators."""

import math
import sys
import os

# Ensure the project src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from indicators.builtin import (
    sma, ema, rsi, macd, bollinger_bands, atr, stochastic_oscillator,
    vwap, obv, ichimoku, fibonacci_retracement, supertrend,
)
from indicators.signals import (
    detect_golden_cross, detect_death_cross, detect_rsi_divergence,
    detect_macd_crossover, detect_bollinger_squeeze,
)


# ── helpers ──────────────────────────────────────────────────────────

def _make_candles(closes, highs=None, lows=None, opens=None, volumes=None):
    """Build candle dicts from price lists."""
    n = len(closes)
    highs = highs or [c + 1 for c in closes]
    lows = lows or [c - 1 for c in closes]
    opens = opens or closes
    volumes = volumes or [1000] * n
    return [
        {"open": opens[i], "high": highs[i], "low": lows[i], "close": closes[i], "volume": volumes[i]}
        for i in range(n)
    ]


def approx(a, b, tol=1e-4):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < tol


# ── SMA / EMA ────────────────────────────────────────────────────────

class TestSMA:
    def test_basic(self):
        prices = [1, 2, 3, 4, 5]
        result = sma(prices, 3)
        assert result[0] is None
        assert result[1] is None
        assert approx(result[2], 2.0)
        assert approx(result[3], 3.0)
        assert approx(result[4], 4.0)

    def test_period_equals_length(self):
        prices = [10, 20, 30]
        result = sma(prices, 3)
        assert approx(result[2], 20.0)


class TestEMA:
    def test_basic(self):
        prices = [1, 2, 3, 4, 5]
        result = ema(prices, 3)
        assert result[0] == 1.0
        assert len(result) == 5
        # EMA should converge toward recent prices
        assert result[-1] > result[0]


# ── RSI ──────────────────────────────────────────────────────────────

class TestRSI:
    def test_all_up(self):
        """All prices going up → RSI near 100."""
        closes = list(range(100, 120))
        candles = _make_candles(closes)
        result = rsi(candles, 14)
        # After warm-up, RSI should be close to 100
        assert result[-1] is not None
        assert result[-1] > 95  # type: ignore

    def test_all_down(self):
        """All prices going down → RSI near 0."""
        closes = list(range(120, 100, -1))
        candles = _make_candles(closes)
        result = rsi(candles, 14)
        assert result[-1] is not None
        assert result[-1] < 5  # type: ignore

    def test_known_values(self):
        """Verify RSI produces values in [0, 100]."""
        import random
        random.seed(42)
        closes = [100 + random.gauss(0, 2) for _ in range(50)]
        candles = _make_candles(closes)
        result = rsi(candles, 14)
        for v in result:
            if v is not None:
                assert 0 <= v <= 100


# ── MACD ─────────────────────────────────────────────────────────────

class TestMACD:
    def test_structure(self):
        closes = [float(i) for i in range(50)]
        candles = _make_candles(closes)
        result = macd(candles)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == 50

    def test_histogram_is_diff(self):
        closes = [100 + i * 0.5 for i in range(50)]
        candles = _make_candles(closes)
        r = macd(candles)
        for m, s, h in zip(r["macd"], r["signal"], r["histogram"]):
            assert approx(h, m - s)


# ── Bollinger Bands ──────────────────────────────────────────────────

class TestBollingerBands:
    def test_structure(self):
        closes = [100.0] * 25
        candles = _make_candles(closes)
        result = bollinger_bands(candles, 20, 2.0)
        assert "upper" in result
        assert "middle" in result
        assert "lower" in result

    def test_constant_price(self):
        """Constant price → bands collapse to the price."""
        closes = [50.0] * 25
        candles = _make_candles(closes)
        r = bollinger_bands(candles, 20, 2.0)
        assert approx(r["upper"][24], 50.0)
        assert approx(r["lower"][24], 50.0)


# ── ATR ──────────────────────────────────────────────────────────────

class TestATR:
    def test_basic(self):
        candles = _make_candles(
            closes=[10, 11, 12, 11, 13, 14, 13, 15, 14, 16, 15, 17, 16, 18, 17],
            highs= [11, 12, 13, 12, 14, 15, 14, 16, 15, 17, 16, 18, 17, 19, 18],
            lows=  [ 9, 10, 11, 10, 12, 13, 12, 14, 13, 15, 14, 16, 15, 17, 16],
        )
        result = atr(candles, 5)
        # After period warm-up, ATR should be positive
        for v in result[4:]:
            assert v is not None and v > 0


# ── Stochastic ───────────────────────────────────────────────────────

class TestStochastic:
    def test_structure(self):
        closes = [float(i) for i in range(20)]
        candles = _make_candles(closes)
        r = stochastic_oscillator(candles, 14, 3)
        assert "k" in r and "d" in r
        assert len(r["k"]) == 20

    def test_range(self):
        import random
        random.seed(99)
        closes = [100 + random.gauss(0, 3) for _ in range(50)]
        candles = _make_candles(closes)
        r = stochastic_oscillator(candles, 14, 3)
        for v in r["k"]:
            if v is not None:
                assert 0 <= v <= 100


# ── VWAP ─────────────────────────────────────────────────────────────

class TestVWAP:
    def test_single(self):
        candles = [{"open": 10, "high": 12, "low": 9, "close": 11, "volume": 100}]
        result = vwap(candles)
        tp = (12 + 9 + 11) / 3
        assert approx(result[0], tp)

    def test_cumulative(self):
        candles = _make_candles([100, 102], volumes=[500, 500])
        result = vwap(candles)
        assert len(result) == 2


# ── OBV ──────────────────────────────────────────────────────────────

class TestOBV:
    def test_basic(self):
        candles = _make_candles([10, 12, 11, 13], volumes=[100, 200, 150, 300])
        result = obv(candles)
        assert result[0] == 100
        assert result[1] == 300   # up → +200
        assert result[2] == 150   # down → -150
        assert result[3] == 450   # up → +300


# ── Ichimoku ─────────────────────────────────────────────────────────

class TestIchimoku:
    def test_structure(self):
        candles = _make_candles([float(i) for i in range(60)])
        r = ichimoku(candles)
        assert "tenkan" in r and "kijun" in r
        assert "senkou_a" in r and "senkou_b" in r and "chikou" in r
        # senkou arrays are displaced forward
        assert len(r["senkou_a"]) == 60 + 26


# ── Fibonacci ────────────────────────────────────────────────────────

class TestFibonacci:
    def test_levels(self):
        candles = _make_candles([100, 110, 90, 105])
        r = fibonacci_retracement(candles)
        assert r["swing_high"] == 111  # high = close + 1
        assert r["swing_low"] == 89    # low = close - 1
        assert approx(r["0.0%"], 111)
        assert approx(r["100.0%"], 89)
        assert approx(r["50.0%"], 100.0)


# ── Supertrend ───────────────────────────────────────────────────────

class TestSupertrend:
    def test_structure(self):
        candles = _make_candles([float(100 + i) for i in range(30)])
        r = supertrend(candles, 10, 3.0)
        assert "supertrend" in r and "direction" in r
        assert len(r["supertrend"]) == 30
        # After warm-up, values should exist
        assert r["supertrend"][15] is not None

    def test_uptrend(self):
        """Steadily rising prices → direction should be 1 (up)."""
        candles = _make_candles([100 + i * 2.0 for i in range(30)])
        r = supertrend(candles, 10, 3.0)
        # Last bars should be uptrend
        assert r["direction"][-1] == 1


# ── Signals ──────────────────────────────────────────────────────────

class TestSignals:
    def test_golden_cross(self):
        # Construct prices where SMA50 crosses above SMA200
        prices = [50.0] * 200 + [100.0] * 100  # jump up
        result = detect_golden_cross(prices, 50, 200)
        crosses = [i for i, v in enumerate(result) if v == "golden_cross"]
        assert len(crosses) > 0

    def test_death_cross(self):
        prices = [100.0] * 200 + [50.0] * 100
        result = detect_death_cross(prices, 50, 200)
        crosses = [i for i, v in enumerate(result) if v == "death_cross"]
        assert len(crosses) > 0

    def test_macd_crossover(self):
        macd_line = [0.0, -1.0, -0.5, 0.5, 1.0]
        signal =    [0.0,  0.0,  0.0, 0.0, 0.0]
        result = detect_macd_crossover(macd_line, signal)
        # Should detect bullish crossover at index 3 (crosses from below to above)
        assert result[3] == "bullish_crossover"

    def test_bollinger_squeeze(self):
        bands = {"bandwidth": [None, 0.05, 0.01, 0.03, 0.005]}
        result = detect_bollinger_squeeze(bands, threshold=0.02)
        assert result[2] == "squeeze"
        assert result[4] == "squeeze"
        assert result[1] is None

    def test_rsi_divergence(self):
        prices = list(range(30, 0, -1))  # descending
        rsi_vals = [None] * 5 + [40, 35, 30, 25, 20, 22, 25, 28, 30, 32,
                                  34, 36, 38, 40, 42, 44, 46, 48, 50, 52,
                                  54, 56, 58, 60, 62]
        result = detect_rsi_divergence(prices, rsi_vals, lookback=10)
        # Just verify it runs and returns correct length
        assert len(result) == len(prices)
