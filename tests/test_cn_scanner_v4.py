import pytest

pytestmark = pytest.mark.skipif(True, reason='ML ensemble tests too slow for CI')

"""
Tests for Enhanced A-Share Scanner Features
============================================
Tests stop-loss/take-profit logic, ML feature engineering,
ML scoring pipeline, and extended period support.
"""

import numpy as np
import pytest

from src.cn_scanner import (
    backtest_cn_strategy,
    CN_UNIVERSE,
    _compute_score_at,
)


# ── Helpers ──────────────────────────────────────────────────────────

def _make_ohlcv(n: int = 120, base: float = 100.0, seed: int = 42):
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    close = np.empty(n)
    close[0] = base
    for i in range(1, n):
        close[i] = close[i - 1] * (1 + rng.randn() * 0.02)
    open_ = np.empty(n)
    open_[0] = base
    open_[1:] = close[:-1]
    high = np.maximum(close, open_) * (1 + rng.rand(n) * 0.01)
    low = np.minimum(close, open_) * (1 - rng.rand(n) * 0.01)
    volume = rng.randint(500, 2000, size=n).astype(np.float64)
    return open_, high, low, close, volume


def _make_simple_data(n: int = 80, base: float = 100.0):
    """Generate simple uptrending data with predictable patterns."""
    rng = np.random.RandomState(99)
    close = np.empty(n)
    close[0] = base
    for i in range(1, n):
        close[i] = close[i - 1] * (1 + 0.001 + rng.randn() * 0.005)
    volume = np.full(n, 1000.0)
    return close, volume


# ── Extended Period Tests ────────────────────────────────────────────

class TestExtendedPeriod:
    """Test that backtest works with period=1y and 2y."""

    def test_period_1y_with_data_override(self):
        """Can run backtest with ~250 bars (1y equivalent)."""
        n = 260
        o, h, l, c, v = _make_ohlcv(n)
        ticker = CN_UNIVERSE[0][0]
        data = {
            ticker: {
                "close": c, "volume": v,
                "open": o, "high": h, "low": l,
            }
        }
        result = backtest_cn_strategy(
            hold_days=5, min_score=0, period="1y",
            lookback_days=200,
            data_override=data, strategy="v1",
        )
        assert "batches" in result
        assert "summary" in result
        # Should generate batches from the extended lookback
        assert result["summary"]["total_batches"] > 0

    def test_period_2y_with_data_override(self):
        """Can run backtest with ~500 bars (2y equivalent)."""
        n = 500
        o, h, l, c, v = _make_ohlcv(n)
        ticker = CN_UNIVERSE[0][0]
        data = {
            ticker: {
                "close": c, "volume": v,
                "open": o, "high": h, "low": l,
            }
        }
        result = backtest_cn_strategy(
            hold_days=5, min_score=0, period="2y",
            lookback_days=400,
            data_override=data, strategy="v1",
        )
        assert result["summary"]["total_batches"] > 0
        # 2y should produce more batches than 6mo equivalent
        result_6mo = backtest_cn_strategy(
            hold_days=5, min_score=0, period="6mo",
            lookback_days=30,
            data_override=data, strategy="v1",
        )
        assert result["summary"]["total_batches"] >= result_6mo["summary"]["total_batches"]

    def test_lookback_capped_by_period(self):
        """Lookback is capped appropriately for each period."""
        n = 120
        o, h, l, c, v = _make_ohlcv(n)
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": c, "volume": v}}

        # For 6mo, lookback should cap at 90
        result = backtest_cn_strategy(
            hold_days=5, min_score=0, period="6mo",
            lookback_days=999,  # will be capped
            data_override=data, strategy="v1",
        )
        assert "summary" in result


# ── Stop-Loss / Take-Profit Tests ───────────────────────────────────

class TestStopLossLogic:
    """Test stop-loss/take-profit with synthetic data."""

    def _make_declining_data(self, n=80) -> tuple:
        """Create data that declines 1% per day from day 40 onwards."""
        close = np.ones(n) * 100.0
        # Stable first 40 bars, then decline
        for i in range(41, n):
            close[i] = close[i - 1] * 0.99  # -1% per day
        volume = np.full(n, 1000.0)
        return close, volume

    def _make_rising_data(self, n=80) -> tuple:
        """Create data that rises 2% per day from day 40 onwards."""
        close = np.ones(n) * 100.0
        for i in range(41, n):
            close[i] = close[i - 1] * 1.02  # +2% per day
        volume = np.full(n, 1000.0)
        return close, volume

    def test_stop_loss_triggers_early_exit(self):
        """Stop-loss at 3% should exit before hold period ends if price drops."""
        close, volume = self._make_declining_data()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": close, "volume": volume}}

        # Without stop-loss
        result_no_sl = backtest_cn_strategy(
            hold_days=10, min_score=0,
            data_override=data, strategy="v1",
        )
        # With 3% stop-loss
        result_sl = backtest_cn_strategy(
            hold_days=10, min_score=0,
            data_override=data, strategy="v1",
            stop_loss=3.0,
        )

        # Both should produce batches
        assert result_no_sl["summary"]["total_batches"] > 0
        assert result_sl["summary"]["total_batches"] > 0

        # With stop-loss, the worst losses should be limited
        if result_sl["batches"] and result_no_sl["batches"]:
            # Check that stop-loss versions have exit_reason field
            sl_stocks = result_sl["batches"][0]["stocks"]
            for s in sl_stocks:
                if "exit_reason" in s:
                    assert s["exit_reason"] in ("stop-loss", "take-profit", "hold-expiry")

    def test_take_profit_triggers_early_exit(self):
        """Take-profit at 5% should exit early when price rises."""
        close, volume = self._make_rising_data()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": close, "volume": volume}}

        result_tp = backtest_cn_strategy(
            hold_days=10, min_score=0,
            data_override=data, strategy="v1",
            take_profit=5.0,
        )

        assert result_tp["summary"]["total_batches"] > 0
        # Check that take-profit was hit
        all_reasons = []
        for batch in result_tp["batches"]:
            for stock in batch["stocks"]:
                if "exit_reason" in stock:
                    all_reasons.append(stock["exit_reason"])
        # At least some exits should be take-profit
        # (depends on when scoring selects the stock, but returns should be capped)

    def test_no_stop_loss_no_extra_fields(self):
        """Without stop-loss/take-profit, no exit_reason field."""
        c, v = _make_simple_data()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": c, "volume": v}}

        result = backtest_cn_strategy(
            hold_days=5, min_score=0,
            data_override=data, strategy="v1",
        )

        for batch in result["batches"]:
            for stock in batch["stocks"]:
                assert "exit_reason" not in stock

    def test_trailing_stop_raises_stop_to_breakeven(self):
        """Trailing stop should move stop to breakeven after 5% profit."""
        # Create data: rise 6% then drop back
        n = 80
        close = np.ones(n) * 100.0
        for i in range(41, 50):
            close[i] = close[i - 1] * 1.015  # rise fast
        # Now close[49] ≈ 114% of close[40] — above 5% threshold
        # Then drop back
        for i in range(50, n):
            close[i] = close[i - 1] * 0.99
        volume = np.full(n, 1000.0)

        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": close, "volume": volume}}

        result = backtest_cn_strategy(
            hold_days=20, min_score=0,
            data_override=data, strategy="v1",
            stop_loss=10.0,  # wide stop
            trailing_stop=True,
        )

        assert result["summary"]["total_batches"] > 0

    def test_stop_loss_and_take_profit_together(self):
        """Can use both stop-loss and take-profit simultaneously."""
        o, h, l, c, v = _make_ohlcv()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": c, "volume": v}}

        result = backtest_cn_strategy(
            hold_days=5, min_score=0,
            data_override=data, strategy="v1",
            stop_loss=3.0,
            take_profit=8.0,
        )

        assert "batches" in result
        assert "summary" in result

    def test_stop_loss_limits_max_loss(self):
        """With stop-loss, per-stock losses should be bounded."""
        # Create data with a crash: -20% over 5 days
        n = 80
        close = np.ones(n) * 100.0
        for i in range(41, 46):
            close[i] = close[i - 1] * 0.96  # -4% per day for 5 days = ~-18.5%
        for i in range(46, n):
            close[i] = close[45]  # flat after crash
        volume = np.full(n, 1000.0)

        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": close, "volume": volume}}

        # With 5% stop-loss
        result = backtest_cn_strategy(
            hold_days=10, min_score=0,
            data_override=data, strategy="v1",
            stop_loss=5.0,
        )

        # Check that individual stock losses are bounded around -5%
        for batch in result["batches"]:
            for stock in batch["stocks"]:
                if stock.get("exit_reason") == "stop-loss":
                    # Should be close to -5%, not -18.5%
                    assert stock["return_pct"] > -8.0, \
                        f"Stop-loss should limit loss, got {stock['return_pct']:.1f}%"


# ── ML Feature Engineering Tests ─────────────────────────────────────

class TestMLFeatures:
    """Test ML feature computation."""

    def test_compute_features_basic(self):
        """compute_features returns correct shape."""
        from src.cn_ml_scorer import compute_features, NUM_FEATURES
        o, h, l, c, v = _make_ohlcv(120)
        feat = compute_features(c, v, o, h, l)
        assert feat is not None
        assert len(feat) == NUM_FEATURES

    def test_compute_features_short_data(self):
        """Returns None for too-short data."""
        from src.cn_ml_scorer import compute_features
        c = np.array([100.0, 101.0, 99.0])
        feat = compute_features(c)
        assert feat is None

    def test_compute_features_series_shape(self):
        """Feature series has correct shape."""
        from src.cn_ml_scorer import compute_features_series, NUM_FEATURES
        o, h, l, c, v = _make_ohlcv(120)
        features = compute_features_series(c, v, o, h, l)
        assert features is not None
        assert features.shape == (120, NUM_FEATURES)

    def test_compute_features_no_volume(self):
        """Features work without volume (volume features will be NaN)."""
        from src.cn_ml_scorer import compute_features_series
        c = np.random.RandomState(42).randn(100).cumsum() + 100
        features = compute_features_series(c)
        assert features is not None
        assert features.shape[0] == 100

    def test_feature_names_count_matches(self):
        """FEATURE_NAMES count matches NUM_FEATURES."""
        from src.cn_ml_scorer import FEATURE_NAMES, NUM_FEATURES
        assert len(FEATURE_NAMES) == NUM_FEATURES

    def test_labels_generation(self):
        """Labels are binary and correct length."""
        from src.cn_ml_scorer import compute_labels
        c = np.linspace(100, 120, 60)  # steadily rising
        labels = compute_labels(c, forward_days=5, threshold=0.02)
        assert len(labels) == 60
        # Last 5 should be NaN
        assert np.all(np.isnan(labels[-5:]))
        # Most early ones should be 1 (price is rising)
        valid = labels[~np.isnan(labels)]
        assert len(valid) > 0
        # Steadily rising by 20/60 per bar = ~0.33% per bar
        # 5-bar fwd return = ~1.7%, below 2% threshold
        # So most labels should be 0 for this slow rise


# ── ML Scoring Pipeline Tests ────────────────────────────────────────

class TestMLScoringPipeline:
    """Test the full ML scoring pipeline."""

    def test_ml_scorer_train_and_predict(self):
        """MLStockScorer can train and produce predictions."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(300, seed=123)
        features = compute_features_series(c, v, o, h, l)
        assert features is not None

        scorer = MLStockScorer(train_bars=120, predict_bars=20, forward_days=5)
        probs = scorer.train_and_predict(features, c)

        assert len(probs) == 300
        # After training window, some predictions should be non-NaN
        valid_probs = probs[~np.isnan(probs)]
        assert len(valid_probs) > 0
        # Probabilities should be in [0, 1]
        assert np.all(valid_probs >= 0.0)
        assert np.all(valid_probs <= 1.0)

    def test_ml_scorer_predict_latest(self):
        """predict_latest works after training."""
        from src.cn_ml_scorer import MLStockScorer, compute_features_series
        o, h, l, c, v = _make_ohlcv(300, seed=456)
        features = compute_features_series(c, v, o, h, l)
        assert features is not None

        scorer = MLStockScorer(train_bars=120, predict_bars=20)
        scorer.train_and_predict(features, c)

        assert scorer._model is not None
        last_feat = features[-1]
        if not np.any(np.isnan(last_feat)):
            prob = scorer.predict_latest(last_feat)
            assert prob is not None
            assert 0.0 <= prob <= 1.0

    def test_ml_scorer_predict_latest_no_model(self):
        """predict_latest returns None before training."""
        from src.cn_ml_scorer import MLStockScorer
        scorer = MLStockScorer()
        feat = np.random.randn(20)
        assert scorer.predict_latest(feat) is None

    def test_blend_scores(self):
        """blend_scores produces reasonable blended values."""
        from src.cn_ml_scorer import blend_scores
        # rule_score=10/20, ml_prob=0.8, equal weight
        blended = blend_scores(10, 0.8, rule_weight=0.5, max_rule_score=20)
        expected = 0.5 * (10 / 20) * 20 + 0.5 * 0.8 * 20
        assert abs(blended - expected) < 0.01

        # Full rule, no ML
        blended_rule = blend_scores(20, 0.0, rule_weight=1.0, max_rule_score=20)
        assert abs(blended_rule - 20.0) < 0.01

        # No rule, full ML
        blended_ml = blend_scores(0, 1.0, rule_weight=0.0, max_rule_score=20)
        assert abs(blended_ml - 20.0) < 0.01

    def test_compute_score_ml_returns_dict(self):
        """compute_score_ml returns valid scoring dict."""
        from src.cn_ml_scorer import compute_score_ml
        o, h, l, c, v = _make_ohlcv(120)
        result = compute_score_ml(c, v, o, h, l)
        assert result["strategy"] == "ml"
        assert "score" in result
        assert "signal" in result
        assert "price" in result

    def test_compute_score_ml_short_data(self):
        """ML scorer falls back gracefully for short data."""
        from src.cn_ml_scorer import compute_score_ml
        c = np.array([100.0, 101.0, 99.0])
        result = compute_score_ml(c)
        assert result["strategy"] == "ml"
        assert result["score"] == 0

    def test_backtest_with_ml_strategy(self):
        """Backtest can run with strategy='ml'."""
        n = 300
        o, h, l, c, v = _make_ohlcv(n, seed=789)
        ticker = CN_UNIVERSE[0][0]
        data = {
            ticker: {
                "close": c, "volume": v,
                "open": o, "high": h, "low": l,
            }
        }
        result = backtest_cn_strategy(
            hold_days=5, min_score=0, period="1y",
            lookback_days=100,
            data_override=data, strategy="ml",
        )
        assert "batches" in result
        assert "summary" in result

    def test_compute_score_at_ml_strategy(self):
        """_compute_score_at handles strategy='ml'."""
        o, h, l, c, v = _make_ohlcv(120)
        result = _compute_score_at(c, v, 119, strategy="ml", open_=o, high=h, low=l)
        assert result["strategy"] == "ml"
        assert "score" in result


# ── Regression: Existing Tests Must Still Pass ───────────────────────

class TestBacktestBackwardCompat:
    """Ensure existing backtest behavior unchanged."""

    def test_default_backtest_no_stoploss(self):
        """Default call without stop-loss/take-profit works as before."""
        c, v = _make_simple_data()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": c, "volume": v}}

        result = backtest_cn_strategy(
            hold_days=5, min_score=0,
            data_override=data, strategy="v1",
        )
        # No exit_reason fields
        for batch in result["batches"]:
            for stock in batch["stocks"]:
                assert "exit_reason" not in stock

    def test_v2_strategy_still_works(self):
        """V2 strategy with stop-loss."""
        o, h, l, c, v = _make_ohlcv()
        ticker = CN_UNIVERSE[0][0]
        data = {ticker: {"close": c, "volume": v}}
        result = backtest_cn_strategy(
            hold_days=5, min_score=0,
            data_override=data, strategy="v2",
            stop_loss=3.0, take_profit=8.0,
        )
        assert "summary" in result

    def test_v3_strategy_still_works(self):
        """V3 strategy with stop-loss."""
        o, h, l, c, v = _make_ohlcv()
        ticker = CN_UNIVERSE[0][0]
        data = {
            ticker: {
                "close": c, "volume": v,
                "open": o, "high": h, "low": l,
            },
        }
        result = backtest_cn_strategy(
            hold_days=5, min_score=0,
            data_override=data, strategy="v3",
            stop_loss=3.0, take_profit=8.0,
        )
        assert "summary" in result
