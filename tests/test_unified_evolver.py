"""
Tests for Unified Evolution System
====================================
Validates all components: UnifiedDNA, cn_scanner signals, Alpha158 factors,
ML training, scoring, backtest, mutation, crossover, evolution.
"""

import math
import os
import sys
import json
import tempfile

import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.evolution.unified_evolver import (
    UnifiedDNA,
    UnifiedEvolver,
    compute_alpha158,
    signal_volume_breakout,
    signal_bottom_reversal,
    signal_macd_divergence,
    signal_ma_alignment,
    signal_low_volume_pullback,
    signal_nday_breakout,
    signal_momentum_confirmation,
    signal_three_soldiers,
    signal_long_lower_shadow,
    signal_doji_at_bottom,
    signal_volume_climax_reversal,
    signal_accumulation,
    signal_rsi_bullish_divergence,
    signal_squeeze_release,
    signal_adx_trend_strength,
    _rsi_np,
    _macd_np,
    _CN_SIGNAL_KEYS,
    _SOURCE_WEIGHT_KEYS,
    _PARAM_RANGES,
)


# ── Fixtures ─────────────────────────────────────────────────────────

def _make_stock_data(n: int = 250, trend: float = 0.001, volatility: float = 0.02, seed: int = 42) -> dict:
    """Generate synthetic stock data for testing."""
    rng = np.random.RandomState(seed)
    base_price = 20.0
    closes = [base_price]
    for _ in range(n - 1):
        ret = trend + rng.randn() * volatility
        closes.append(closes[-1] * (1 + ret))
    closes = np.array(closes)
    opens = closes * (1 + rng.randn(n) * 0.005)
    highs = np.maximum(opens, closes) * (1 + np.abs(rng.randn(n) * 0.01))
    lows = np.minimum(opens, closes) * (1 - np.abs(rng.randn(n) * 0.01))
    volumes = np.abs(rng.randn(n) * 1e6 + 5e6)
    dates = [f"2024-{(i // 22 + 1):02d}-{(i % 22 + 1):02d}" for i in range(n)]

    return {
        "date": dates,
        "open": opens.tolist(),
        "high": highs.tolist(),
        "low": lows.tolist(),
        "close": closes.tolist(),
        "volume": volumes.tolist(),
    }


def _make_csv_dir(num_stocks: int = 5, n: int = 200) -> str:
    """Create a temp dir with synthetic CSV files."""
    tmpdir = tempfile.mkdtemp(prefix="finclaw_test_")
    for i in range(num_stocks):
        sd = _make_stock_data(n=n, seed=42 + i)
        code = f"sh_60051{i}"
        csv_path = os.path.join(tmpdir, f"{code}.csv")
        with open(csv_path, "w") as f:
            f.write("date,code,open,high,low,close,volume,amount,turn\n")
            for j in range(len(sd["date"])):
                amount = sd["close"][j] * sd["volume"][j]
                f.write(
                    f"{sd['date'][j]},{code},"
                    f"{sd['open'][j]:.4f},{sd['high'][j]:.4f},"
                    f"{sd['low'][j]:.4f},{sd['close'][j]:.4f},"
                    f"{sd['volume'][j]:.0f},{amount:.0f},0.5\n"
                )
    return tmpdir


# ── Test 1: UnifiedDNA serialization ─────────────────────────────────

def test_01_dna_serialization():
    """UnifiedDNA can round-trip through dict."""
    dna = UnifiedDNA()
    d = dna.to_dict()
    assert isinstance(d, dict)
    assert "w_cn_scanner" in d
    assert "ml_n_estimators" in d
    assert "stop_loss_pct" in d

    dna2 = UnifiedDNA.from_dict(d)
    assert dna2.w_cn_scanner == dna.w_cn_scanner
    assert dna2.ml_n_estimators == dna.ml_n_estimators
    assert dna2.hold_days == dna.hold_days

    # Extra keys are ignored
    d["unknown_key"] = 999
    dna3 = UnifiedDNA.from_dict(d)
    assert dna3.w_cn_scanner == dna.w_cn_scanner


def test_02_dna_weights_normalize():
    """Source and signal weights normalize correctly."""
    dna = UnifiedDNA(w_cn_scanner=0.6, w_ml=0.2, w_technical=0.2)
    w_cn, w_ml, w_tech = dna.get_source_weights()
    assert abs(w_cn + w_ml + w_tech - 1.0) < 1e-6
    assert abs(w_cn - 0.6) < 1e-6

    signal_w = dna.get_signal_weights()
    assert len(signal_w) == 15
    assert abs(sum(signal_w.values()) - 1.0) < 1e-6


# ── Test 3: cn_scanner signals fire on synthetic data ────────────────

def test_03_cn_signals_return_valid_scores():
    """All 15 signal functions return values in [0, 10]."""
    sd = _make_stock_data(n=250)
    closes = np.array(sd["close"])
    volumes = np.array(sd["volume"])
    opens = np.array(sd["open"])
    highs = np.array(sd["high"])
    lows = np.array(sd["low"])
    rsi_arr = _rsi_np(closes)
    _, _, macd_hist = _macd_np(closes)

    idx = 100
    signals = {
        "volume_breakout": signal_volume_breakout(closes, volumes, idx),
        "bottom_reversal": signal_bottom_reversal(closes, rsi_arr, idx),
        "macd_divergence": signal_macd_divergence(closes, macd_hist, idx),
        "ma_alignment": signal_ma_alignment(closes, idx),
        "low_volume_pullback": signal_low_volume_pullback(closes, volumes, idx),
        "nday_breakout": signal_nday_breakout(closes, idx),
        "momentum_confirmation": signal_momentum_confirmation(closes, idx),
        "three_soldiers": signal_three_soldiers(opens, highs, lows, closes, idx),
        "long_lower_shadow": signal_long_lower_shadow(opens, highs, lows, closes, rsi_arr, idx),
        "doji_at_bottom": signal_doji_at_bottom(opens, closes, volumes, rsi_arr, idx),
        "volume_climax_reversal": signal_volume_climax_reversal(closes, volumes, idx),
        "accumulation": signal_accumulation(closes, volumes, idx),
        "rsi_divergence": signal_rsi_bullish_divergence(closes, rsi_arr, idx),
        "squeeze_release": signal_squeeze_release(closes, idx),
        "adx_trend": signal_adx_trend_strength(highs, lows, closes, idx),
    }

    assert len(signals) == 15
    for name, val in signals.items():
        assert 0.0 <= val <= 10.0, f"Signal {name} out of range: {val}"


def test_04_cn_signals_edge_cases():
    """Signals handle edge cases (insufficient data)."""
    short = np.array([10.0, 10.5, 10.3])
    vols = np.array([1e6, 1.1e6, 0.9e6])
    rsi_arr = np.array([50.0, 50.0, 50.0])

    assert signal_volume_breakout(short, vols, 0) == 0.0
    assert signal_volume_breakout(short, vols, 2) == 0.0
    assert signal_ma_alignment(short, 2) == 0.0
    assert signal_nday_breakout(short, 2) == 0.0
    assert signal_momentum_confirmation(short, 2) == 0.0


# ── Test 5: Alpha158 factor computation ──────────────────────────────

def test_05_alpha158_factors():
    """Alpha158 produces expected number of features."""
    sd = _make_stock_data(n=200)
    dates = np.array(sd["date"])
    opens = np.array(sd["open"])
    highs = np.array(sd["high"])
    lows = np.array(sd["low"])
    closes = np.array(sd["close"])
    volumes = np.array(sd["volume"])

    X, y, names = compute_alpha158(dates, opens, highs, lows, closes, volumes)

    assert X is not None
    assert y is not None
    assert names is not None
    assert X.shape[0] == 200  # same as input length
    assert X.shape[1] == len(names)
    # Default DNA uses all factor groups: 9 KBAR + 5 windows × (ROC+MA+STD+BETA+2MAX+RSV+CORR+2CNTP+VMA=11)
    # = 9 + 55 = 64
    assert X.shape[1] == 64, f"Expected 64 features, got {X.shape[1]}"
    assert len(names) == 64


def test_06_alpha158_feature_selection():
    """Alpha158 respects DNA feature selection flags."""
    sd = _make_stock_data(n=200)
    dates = np.array(sd["date"])
    opens = np.array(sd["open"])
    highs = np.array(sd["high"])
    lows = np.array(sd["low"])
    closes = np.array(sd["close"])
    volumes = np.array(sd["volume"])

    # Only KBAR + ROC
    dna = UnifiedDNA(
        use_kbar=True, use_roc=True, use_ma=False, use_std=False,
        use_beta=False, use_maxmin=False, use_rsv=False, use_corr=False,
        use_cntp=False, use_vma=False,
    )
    X, _, names = compute_alpha158(dates, opens, highs, lows, closes, volumes, dna)
    assert X is not None
    # 9 KBAR + 5 ROC = 14
    assert X.shape[1] == 14, f"Expected 14 features, got {X.shape[1]}"
    assert all(n.startswith("K") or n.startswith("ROC") for n in names)


# ── Test 7: Unified scoring ─────────────────────────────────────────

def test_07_unified_scoring():
    """Unified scoring returns a reasonable value."""
    tmpdir = _make_csv_dir(num_stocks=3, n=200)
    evolver = UnifiedEvolver(tmpdir, seed=42)
    data = evolver.load_elite_pool()
    assert len(data) > 0

    code = list(data.keys())[0]
    sd = data[code]
    dna = UnifiedDNA()

    score = evolver.score_stock(sd, 100, dna)
    assert isinstance(score, float)
    assert 0.0 <= score <= 10.0, f"Score out of range: {score}"


# ── Test 8: Backtest produces valid metrics ──────────────────────────

def test_08_backtest():
    """Backtest returns all expected metrics."""
    tmpdir = _make_csv_dir(num_stocks=5, n=200)
    evolver = UnifiedEvolver(tmpdir, seed=42)
    data = evolver.load_elite_pool()
    dna = UnifiedDNA(hold_days=3, max_positions=2, min_score=2.0)

    result = evolver.backtest(dna, data)

    assert "annual_return" in result
    assert "max_drawdown" in result
    assert "win_rate" in result
    assert "sharpe" in result
    assert "calmar" in result
    assert "total_trades" in result
    assert "profit_factor" in result
    assert "fitness" in result
    assert "dna" in result
    assert result["max_drawdown"] >= 0.0
    assert 0.0 <= result["win_rate"] <= 100.0


# ── Test 9: Mutation and crossover ───────────────────────────────────

def test_09_mutation_crossover():
    """Mutation creates different DNA; crossover combines parents."""
    evolver = UnifiedEvolver("dummy", seed=42)
    dna = UnifiedDNA()

    # Mutation should change at least something
    mutated = evolver.mutate(dna)
    d_orig = dna.to_dict()
    d_mut = mutated.to_dict()
    changed = sum(1 for k in d_orig if d_orig[k] != d_mut[k])
    assert changed > 0, "Mutation didn't change anything"

    # Source weights should still be normalized
    w_cn, w_ml, w_tech = mutated.get_source_weights()
    assert abs(w_cn + w_ml + w_tech - 1.0) < 1e-4

    # Crossover
    dna2 = UnifiedDNA(w_cn_scanner=0.8, w_ml=0.1, w_technical=0.1)
    child = evolver.crossover(dna, dna2)
    d_child = child.to_dict()
    # Child should have some params from each parent
    from_p1 = sum(1 for k in d_orig if d_child.get(k) == d_orig[k])
    from_p2 = sum(1 for k in d_orig if d_child.get(k) == dna2.to_dict().get(k))
    assert from_p1 > 0 or from_p2 > 0, "Crossover didn't mix parents"


# ── Test 10: Evolution runs and improves ─────────────────────────────

def test_10_evolution_basic():
    """Evolution loop runs without errors and produces results."""
    tmpdir = _make_csv_dir(num_stocks=5, n=150)
    evolver = UnifiedEvolver(
        tmpdir, seed=42,
        population_size=6, elite_count=2,
        results_dir=os.path.join(tmpdir, "evo_results"),
    )
    results = evolver.evolve(generations=3, population=6, use_ml=False, save_interval=2)

    assert len(results) > 0
    assert results[0]["fitness"] >= results[-1]["fitness"]
    assert results[0]["total_trades"] >= 0

    # Check that results were saved
    latest = os.path.join(tmpdir, "evo_results", "latest.json")
    assert os.path.exists(latest)
    with open(latest) as f:
        saved = json.load(f)
    assert saved["system"] == "unified_evolution"


# ── Test 11: Elite pool filtering ────────────────────────────────────

def test_11_elite_pool_filtering():
    """Stock pool filtering works with quality criteria."""
    tmpdir = _make_csv_dir(num_stocks=10, n=200)
    dna = UnifiedDNA(min_price=5.0, min_daily_amount=1000.0, max_stocks=5)
    evolver = UnifiedEvolver(tmpdir, best_dna=dna, seed=42)
    data = evolver.load_elite_pool()

    # Should have at most max_stocks
    assert len(data) <= 5


# ── Test 12: ML model training ──────────────────────────────────────

def test_12_ml_model_training():
    """ML model trains and predicts without error."""
    tmpdir = _make_csv_dir(num_stocks=5, n=200)
    evolver = UnifiedEvolver(tmpdir, seed=42)
    data = evolver.load_elite_pool()
    dna = UnifiedDNA(ml_n_estimators=10, ml_max_depth=3)

    model = evolver.train_ml_model(data, dna)
    # Model may be None if not enough valid data, but should not raise
    if model is not None:
        # Test prediction
        code = list(data.keys())[0]
        sd = data[code]
        features = evolver.compute_alpha158_features(sd, 100, dna)
        if features is not None:
            pred = model.predict(features.reshape(1, -1))
            assert len(pred) == 1
            assert np.isfinite(pred[0])


# ── Test 13: cn_scanner signal computation via evolver ───────────────

def test_13_evolver_cn_signals():
    """UnifiedEvolver.compute_cn_scanner_signals returns all 15 signals."""
    tmpdir = _make_csv_dir(num_stocks=1, n=200)
    evolver = UnifiedEvolver(tmpdir, seed=42)
    data = evolver.load_elite_pool()
    code = list(data.keys())[0]
    sd = data[code]

    signals = evolver.compute_cn_scanner_signals(sd, 100)
    assert len(signals) == 15
    expected_keys = {
        "volume_breakout", "bottom_reversal", "macd_divergence",
        "ma_alignment", "low_volume_pullback", "nday_breakout",
        "momentum_confirmation", "three_soldiers", "long_lower_shadow",
        "doji_at_bottom", "volume_climax_reversal", "accumulation",
        "rsi_divergence", "squeeze_release", "adx_trend",
    }
    assert set(signals.keys()) == expected_keys
    for v in signals.values():
        assert 0.0 <= v <= 10.0


# ── Test 14: Param ranges cover all mutable params ──────────────────

def test_14_param_ranges():
    """All numeric DNA params have defined ranges for mutation."""
    dna = UnifiedDNA()
    d = dna.to_dict()
    for key, val in d.items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            assert key in _PARAM_RANGES, f"Missing range for param: {key}"
        if isinstance(val, bool):
            # Booleans aren't mutated via _PARAM_RANGES, that's fine
            pass


# ── Test 15: Fitness function ────────────────────────────────────────

def test_15_fitness():
    """Fitness computation rewards good metrics and penalizes few trades."""
    f1 = UnifiedEvolver._compute_fitness(100.0, 10.0, 60.0, 2.0, 100)
    f2 = UnifiedEvolver._compute_fitness(100.0, 10.0, 60.0, 2.0, 5)
    # Few trades should be penalized
    assert f1 > f2

    # Higher return → higher fitness
    f3 = UnifiedEvolver._compute_fitness(200.0, 10.0, 60.0, 2.0, 100)
    assert f3 > f1

    # Higher drawdown → lower fitness
    f4 = UnifiedEvolver._compute_fitness(100.0, 30.0, 60.0, 2.0, 100)
    assert f1 > f4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
