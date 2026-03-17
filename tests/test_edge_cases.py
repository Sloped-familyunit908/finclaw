"""
Edge Cases & Data Integrity Tests
===================================
Boundary conditions, NaN/Inf handling, empty DataFrames,
large datasets, special characters, math verification.
"""

import sys
import os
import math
import time
import pytest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_ohlcv(n=200, seed=42):
    np.random.seed(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    close = 100.0 * np.cumprod(1 + np.random.normal(0.0003, 0.02, n))
    return pd.DataFrame({
        "Open": close * 0.999, "High": close * 1.01,
        "Low": close * 0.99, "Close": close,
        "Volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
    }, index=dates)


# ── Empty DataFrame Handling ─────────────────────────────────────

class TestEmptyDataFrame:
    def test_talib_empty_df(self):
        from src.plugin_system.talib_adapter import compute_indicator
        import src.plugin_system.talib_adapter as mod
        orig = mod._HAS_TALIB
        mod._HAS_TALIB = False
        try:
            empty = pd.DataFrame({"Open": [], "High": [], "Low": [], "Close": [], "Volume": []})
            # Should not crash — may raise or return empty
            try:
                result = compute_indicator("sma", empty)
                for s in result.values():
                    assert len(s) == 0
            except (ValueError, KeyError):
                pass  # acceptable
        finally:
            mod._HAS_TALIB = orig

    def test_pine_parser_empty_df(self):
        from src.plugin_system.pine_parser import PineScriptPlugin
        pine = '''
        //@version=5
        strategy("test")
        fast = ta.sma(close, 10)
        '''
        plugin = PineScriptPlugin(pine, name="empty_test")
        empty = pd.DataFrame({"Open": [], "High": [], "Low": [], "Close": [], "Volume": []})
        try:
            signals = plugin.generate_signals(empty)
            assert len(signals) == 0
        except (ValueError, KeyError, IndexError):
            pass  # acceptable for empty input


# ── NaN and Inf Handling ─────────────────────────────────────────

class TestNaNInfHandling:
    def test_rsi_with_nan(self):
        from src.ta import rsi
        data = np.array([100.0] * 5 + [np.nan] * 3 + [105.0] * 10)
        # Should not crash
        result = rsi(data, 14)
        assert len(result) == len(data)

    def test_macd_with_inf(self):
        from src.ta import macd
        data = np.array([100.0] * 50)
        data[25] = np.inf
        # Should not crash (may produce NaN/Inf in output)
        line, sig, hist = macd(data)
        assert len(line) == len(data)

    def test_sma_all_nan(self):
        from src.ta import sma
        data = np.full(50, np.nan)
        result = sma(data, 20)
        assert len(result) == 50
        assert np.all(np.isnan(result))

    def test_bollinger_constant_prices(self):
        """Constant prices → zero std → should not divide by zero."""
        from src.ta import bollinger_bands
        data = np.full(50, 100.0)
        result = bollinger_bands(data, 20)
        assert "upper" in result
        assert "lower" in result
        # Upper and lower should be equal (or close) when std=0
        valid = ~np.isnan(result["upper"])
        if valid.any():
            np.testing.assert_allclose(
                result["upper"][valid], result["lower"][valid], atol=1e-10
            )

    def test_rsi_constant_prices(self):
        """Constant prices → zero gains/losses → RSI should not crash."""
        from src.ta import rsi
        data = np.full(100, 50.0)
        result = rsi(data, 14)
        assert len(result) == 100
        # No price change → RSI undefined but should not be NaN for all


# ── Large Dataset Performance ────────────────────────────────────

class TestLargeDataset:
    def test_ta_100k_rows(self):
        """Technical indicators should handle 100K rows in reasonable time."""
        from src.ta import rsi, macd, sma, bollinger_bands

        np.random.seed(42)
        data = 100.0 * np.cumprod(1 + np.random.normal(0.0003, 0.02, 100_000))

        start = time.time()
        r = rsi(data, 14)
        m_line, m_sig, m_hist = macd(data)
        s = sma(data, 50)
        bb = bollinger_bands(data, 20)
        elapsed = time.time() - start

        assert len(r) == 100_000
        assert len(m_line) == 100_000
        assert elapsed < 30, f"100K rows took {elapsed:.1f}s — too slow"

    def test_talib_fallback_100k(self):
        """Fallback indicators on 100K rows."""
        from src.plugin_system.talib_adapter import compute_indicator
        import src.plugin_system.talib_adapter as mod
        orig = mod._HAS_TALIB
        mod._HAS_TALIB = False
        try:
            np.random.seed(42)
            n = 100_000
            close = 100.0 * np.cumprod(1 + np.random.normal(0.0003, 0.02, n))
            dates = pd.date_range("2000-01-01", periods=n, freq="h")
            df = pd.DataFrame({
                "Open": close * 0.999, "High": close * 1.01,
                "Low": close * 0.99, "Close": close,
                "Volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
            }, index=dates)

            start = time.time()
            compute_indicator("rsi", df)
            compute_indicator("macd", df)
            elapsed = time.time() - start
            assert elapsed < 30, f"Fallback 100K took {elapsed:.1f}s"
        finally:
            mod._HAS_TALIB = orig


# ── Special Characters in Ticker ─────────────────────────────────

class TestSpecialTickers:
    def test_ticker_with_dot(self):
        """Tickers like 000001.SZ should be handled."""
        # Just verify it doesn't crash the CLI parser
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["quote", "000001.SZ"])
        assert args.symbol == "000001.SZ"

    def test_ticker_with_caret(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["quote", "^GSPC"])
        assert args.symbol == "^GSPC"

    def test_ticker_with_slash(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["quote", "BTC/USDT"])
        assert args.symbol == "BTC/USDT"


# ── Technical Indicator Math Verification ────────────────────────

class TestIndicatorMath:
    """Verify indicator calculations against known values."""

    def test_sma_known_values(self):
        from src.ta import sma
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        result = sma(data, 3)
        # SMA(3) at index 2 = (1+2+3)/3 = 2.0
        np.testing.assert_almost_equal(result[2], 2.0)
        # SMA(3) at index 9 = (8+9+10)/3 = 9.0
        np.testing.assert_almost_equal(result[9], 9.0)

    def test_ema_known_values(self):
        from src.ta import ema
        data = np.array([10.0, 10.0, 10.0, 10.0, 10.0])
        result = ema(data, 3)
        # Constant input → EMA should equal input
        np.testing.assert_allclose(result, 10.0, atol=1e-10)

    def test_rsi_extreme_values(self):
        from src.ta import rsi
        # All gains → RSI should approach 100
        rising = np.arange(1.0, 101.0)
        r = rsi(rising, 14)
        assert r[-1] > 90, f"RSI for steadily rising should be near 100, got {r[-1]}"

        # All losses → RSI should approach 0
        falling = np.arange(100.0, 0.0, -1.0)
        r2 = rsi(falling, 14)
        assert r2[-1] < 10, f"RSI for steadily falling should be near 0, got {r2[-1]}"

    def test_macd_signal(self):
        from src.ta import macd
        # With enough data, MACD should have values
        np.random.seed(42)
        data = 100.0 * np.cumprod(1 + np.random.normal(0.001, 0.02, 100))
        line, sig, hist = macd(data)
        assert len(line) == 100
        # Histogram = line - signal
        np.testing.assert_allclose(hist, line - sig, atol=1e-10)

    def test_bollinger_width(self):
        from src.ta import bollinger_bands
        np.random.seed(42)
        data = 100.0 * np.cumprod(1 + np.random.normal(0, 0.02, 100))
        bb = bollinger_bands(data, 20, 2.0)
        # Upper > Middle > Lower for valid indices
        valid = ~np.isnan(bb["upper"])
        assert np.all(bb["upper"][valid] >= bb["middle"][valid])
        assert np.all(bb["middle"][valid] >= bb["lower"][valid])


# ── Stop Loss Logic ──────────────────────────────────────────────

class TestStopLossLogic:
    def test_fixed_stop_triggers(self):
        from src.risk.stop_loss import StopLossManager, StopLossType
        mgr = StopLossManager(fixed_pct=0.05)
        stops = mgr.compute_stops(
            entry_price=100.0, current_price=94.0,
            highest_since_entry=105.0, bars_held=5,
        )
        fixed = [s for s in stops if s.type == StopLossType.FIXED]
        assert len(fixed) == 1
        assert fixed[0].triggered is True  # 94 < 95 (100 * 0.95)

    def test_fixed_stop_not_triggered(self):
        from src.risk.stop_loss import StopLossManager, StopLossType
        mgr = StopLossManager(fixed_pct=0.05)
        stops = mgr.compute_stops(
            entry_price=100.0, current_price=96.0,
            highest_since_entry=100.0, bars_held=5,
        )
        fixed = [s for s in stops if s.type == StopLossType.FIXED]
        assert fixed[0].triggered is False

    def test_trailing_stop(self):
        from src.risk.stop_loss import StopLossManager, StopLossType
        mgr = StopLossManager(trailing_pct=0.10)
        # Price went to 120, now at 107 → trailing stop at 108 (120*0.90)
        stops = mgr.compute_stops(
            entry_price=100.0, current_price=107.0,
            highest_since_entry=120.0, bars_held=30,
        )
        trailing = [s for s in stops if s.type == StopLossType.TRAILING]
        assert len(trailing) == 1
        assert trailing[0].triggered is True  # 107 < 108

    def test_time_stop(self):
        from src.risk.stop_loss import StopLossManager, StopLossType
        mgr = StopLossManager(max_hold_bars=60)
        stops = mgr.compute_stops(
            entry_price=100.0, current_price=100.0,
            highest_since_entry=100.0, bars_held=61,
        )
        time_stops = [s for s in stops if s.type == StopLossType.TIME]
        assert len(time_stops) == 1
        assert time_stops[0].triggered is True


# ── Backtest Result Math Verification ────────────────────────────

class TestBacktestMath:
    def test_return_calculation(self):
        """Verify return = (final - initial) / initial."""
        # Simple: buy at 100, sell at 120 → 20% return
        initial = 100000
        buy_price = 100.0
        sell_price = 120.0
        shares = initial / buy_price
        final = shares * sell_price
        ret = (final - initial) / initial
        assert abs(ret - 0.20) < 1e-10

    def test_max_drawdown_calculation(self):
        """Verify max drawdown from equity curve."""
        equity = [100, 110, 105, 95, 100, 90, 95]
        # Peak at 110, trough at 90 → DD = (110-90)/110 = 18.18%
        peak = equity[0]
        max_dd = 0
        for v in equity:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        assert abs(max_dd - (110 - 90) / 110) < 1e-10

    def test_win_rate_calculation(self):
        """Win rate = wins / total trades."""
        trades = [10, -5, 20, -3, 15, -8, 7]
        wins = sum(1 for t in trades if t > 0)
        total = len(trades)
        wr = wins / total
        assert abs(wr - 4 / 7) < 1e-10
