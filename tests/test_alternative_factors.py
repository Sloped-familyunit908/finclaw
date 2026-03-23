"""Tests for alternative data factors — Phase 3 of evolution engine."""

import math
import sys
import os
import importlib.util
from pathlib import Path

import pytest

# ── Constants ─────────────────────────────────────────────────────

FACTORS_DIR = Path(__file__).parent.parent / "factors"

# All new factor files
NEW_FACTOR_FILES = [
    "money_flow_smart.py",
    "money_flow_volume_price_confirmation.py",
    "money_flow_liquidity_shock.py",
    "sector_relative_strength.py",
    "sector_momentum_rank.py",
    "sector_breadth_thrust.py",
    "regime_fear_greed_proxy.py",
    "regime_earnings_drift_proxy.py",
    "regime_dispersion_signal.py",
    "regime_capitulation_recovery.py",
]

NEW_FACTOR_NAMES = [
    "smart_money_flow",
    "volume_price_confirmation",
    "liquidity_shock",
    "relative_strength_vs_market",
    "sector_momentum_rank",
    "breadth_thrust",
    "fear_greed_proxy",
    "earnings_drift_proxy",
    "dispersion_signal",
    "capitulation_recovery",
]


# ── Helpers ───────────────────────────────────────────────────────

def _load_factor_module(filename):
    """Load a factor module from factors/ directory."""
    path = FACTORS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_uptrend_data(n=100):
    """Create synthetic uptrend data."""
    closes = [10.0 + i * 0.1 for i in range(n)]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.2 for c in closes]
    volumes = [1000000.0 + (i % 5) * 50000 for i in range(n)]
    return closes, highs, lows, volumes


def _make_downtrend_data(n=100):
    """Create synthetic downtrend data."""
    closes = [20.0 - i * 0.1 for i in range(n)]
    closes = [max(c, 1.0) for c in closes]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.2 for c in closes]
    volumes = [1000000.0 + (i % 5) * 50000 for i in range(n)]
    return closes, highs, lows, volumes


def _make_flat_data(n=100):
    """Create synthetic flat data."""
    closes = [10.0] * n
    highs = [10.3] * n
    lows = [9.7] * n
    volumes = [1000000.0] * n
    return closes, highs, lows, volumes


def _make_volatile_data(n=100):
    """Create highly volatile synthetic data."""
    import math as m
    closes = [10.0 + 2.0 * m.sin(i * 0.5) for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    volumes = [1000000.0 + 500000 * abs(m.sin(i * 0.3)) for i in range(n)]
    return closes, highs, lows, volumes


def _make_capitulation_data(n=80):
    """Create data with capitulation pattern: 5 red days with increasing volume, then reversal."""
    closes = [20.0 + i * 0.05 for i in range(n - 10)]
    # Add 5 consecutive red days with increasing volume
    last_close = closes[-1]
    for d in range(5):
        last_close *= 0.97  # 3% drop each day
        closes.append(last_close)
    # Add reversal candle
    closes.append(last_close * 1.03)
    # Fill remaining
    while len(closes) < n:
        closes.append(closes[-1] * 1.01)

    highs = [c + 0.5 for c in closes]
    lows = [c - 0.3 for c in closes]
    # Make volume increase during capitulation
    volumes = [1000000.0] * (n - 10)
    for d in range(5):
        volumes.append(2000000 + d * 1000000)  # 2M, 3M, 4M, 5M, 6M
    volumes.append(3000000)  # reversal day high volume
    while len(volumes) < n:
        volumes.append(1000000)

    # Fix lows for reversal candle: long lower shadow
    rev_idx = n - 10 + 5
    if rev_idx < n:
        lows[rev_idx] = closes[rev_idx] - 1.5  # long lower shadow

    return closes, highs, lows, volumes


def _make_volume_spike_data(n=100):
    """Create data with a volume spike at a specific day."""
    closes = [10.0 + i * 0.05 for i in range(n)]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.2 for c in closes]
    volumes = [1000000.0] * n
    # Spike at idx 80: 5x normal volume with positive close
    if n > 80:
        volumes[80] = 5000000.0
        closes[80] = closes[79] * 1.05  # 5% positive move
        highs[80] = closes[80] + 0.5
    return closes, highs, lows, volumes


def _make_gap_data(n=100):
    """Create data with a significant gap-up."""
    closes = [10.0 + i * 0.02 for i in range(n)]
    highs = [c + 0.3 for c in closes]
    lows = [c - 0.2 for c in closes]
    volumes = [1000000.0] * n
    # Gap at idx 70: 5% gap up followed by continuation
    if n > 75:
        gap_base = closes[69]
        closes[70] = gap_base * 1.05
        highs[70] = closes[70] + 0.5
        lows[70] = gap_base * 1.03
        # Continuation over next 5 days
        for i in range(71, 76):
            closes[i] = closes[i - 1] * 1.01
            highs[i] = closes[i] + 0.3
            lows[i] = closes[i] - 0.2
    return closes, highs, lows, volumes


# ══════════════════════════════════════════════════════════════════
# 1. Factor file loadability
# ══════════════════════════════════════════════════════════════════

class TestFactorLoadability:
    """Test that all new factor files can be loaded by FactorRegistry."""

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_factor_file_loadable(self, filename):
        """Each factor file should be importable and have required attributes."""
        mod = _load_factor_module(filename)
        assert hasattr(mod, "FACTOR_NAME"), f"{filename} missing FACTOR_NAME"
        assert hasattr(mod, "FACTOR_DESC"), f"{filename} missing FACTOR_DESC"
        assert hasattr(mod, "FACTOR_CATEGORY"), f"{filename} missing FACTOR_CATEGORY"
        assert hasattr(mod, "compute"), f"{filename} missing compute function"
        assert callable(mod.compute), f"{filename}.compute not callable"

    def test_factor_registry_loads_all(self):
        """FactorRegistry should load all new factors."""
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.evolution.factor_discovery import FactorRegistry

        registry = FactorRegistry(str(FACTORS_DIR))
        loaded = registry.load_all()
        factor_names = registry.list_factors()

        for name in NEW_FACTOR_NAMES:
            assert name in factor_names, f"FactorRegistry did not load factor '{name}'"

    @pytest.mark.parametrize("filename,expected_name", list(zip(NEW_FACTOR_FILES, NEW_FACTOR_NAMES)))
    def test_factor_name_matches(self, filename, expected_name):
        """FACTOR_NAME should match expected value."""
        mod = _load_factor_module(filename)
        assert mod.FACTOR_NAME == expected_name


# ══════════════════════════════════════════════════════════════════
# 2. Return type and range checks
# ══════════════════════════════════════════════════════════════════

class TestFactorReturnRange:
    """Every factor must return a float in [0, 1]."""

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_returns_float_in_range_uptrend(self, filename):
        """Factor returns float in [0, 1] for uptrend data."""
        mod = _load_factor_module(filename)
        closes, highs, lows, volumes = _make_uptrend_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert isinstance(result, (int, float)), f"Expected float, got {type(result)}"
        assert 0.0 <= result <= 1.0, f"Out of range: {result}"
        assert not math.isnan(result), "NaN returned"
        assert not math.isinf(result), "Inf returned"

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_returns_float_in_range_downtrend(self, filename):
        """Factor returns float in [0, 1] for downtrend data."""
        mod = _load_factor_module(filename)
        closes, highs, lows, volumes = _make_downtrend_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0, f"Out of range: {result}"

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_returns_float_volatile_data(self, filename):
        """Factor returns float in [0, 1] for volatile data."""
        mod = _load_factor_module(filename)
        closes, highs, lows, volumes = _make_volatile_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0, f"Out of range: {result}"


# ══════════════════════════════════════════════════════════════════
# 3. Edge cases
# ══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case handling: idx=0, short arrays, all-zero volumes."""

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_idx_zero(self, filename):
        """Factor should handle idx=0 gracefully."""
        mod = _load_factor_module(filename)
        closes = [10.0]
        highs = [10.5]
        lows = [9.5]
        volumes = [1000000.0]
        result = mod.compute(closes, highs, lows, volumes, 0)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_very_short_arrays(self, filename):
        """Factor should handle arrays with only 3 elements."""
        mod = _load_factor_module(filename)
        closes = [10.0, 10.1, 10.2]
        highs = [10.5, 10.6, 10.7]
        lows = [9.5, 9.6, 9.7]
        volumes = [1000000.0, 1100000.0, 1200000.0]
        result = mod.compute(closes, highs, lows, volumes, 2)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_all_zero_volumes(self, filename):
        """Factor should handle all-zero volumes without error."""
        mod = _load_factor_module(filename)
        closes = [10.0 + i * 0.1 for i in range(50)]
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.2 for c in closes]
        volumes = [0.0] * 50
        result = mod.compute(closes, highs, lows, volumes, 49)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0

    @pytest.mark.parametrize("filename", NEW_FACTOR_FILES)
    def test_flat_prices(self, filename):
        """Factor should handle flat price data."""
        mod = _load_factor_module(filename)
        closes, highs, lows, volumes = _make_flat_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert isinstance(result, (int, float))
        assert 0.0 <= result <= 1.0


# ══════════════════════════════════════════════════════════════════
# 4. Synthetic data pattern tests (known signals)
# ══════════════════════════════════════════════════════════════════

class TestSmartMoneyFlow:
    """Test smart_money_flow factor with known patterns."""

    def test_institutional_buying_high_score(self):
        """Large volume + positive close days should give score > 0.5."""
        mod = _load_factor_module("money_flow_smart.py")
        # 50 days: first 40 baseline, last 10 have institutional buying
        # The avg vol window is 20 days BEFORE idx, so use enough baseline
        n = 50
        closes = [10.0] * n
        highs = [10.3] * n
        lows = [9.7] * n
        volumes = [1000000.0] * n
        # Last 5 days only: very large volume with positive moves
        # This keeps 20-day avg window (days 29-48) mostly baseline
        for i in range(45, 50):
            volumes[i] = 5000000.0  # 5x baseline
            closes[i] = closes[i - 1] * 1.03  # strong positive close
            highs[i] = closes[i] + 0.3
            lows[i] = closes[i] - 0.2
        result = mod.compute(closes, highs, lows, volumes, 49)
        assert result > 0.5, f"Expected > 0.5 for institutional buying, got {result}"

    def test_no_large_volume_neutral(self):
        """No large volume bars should give neutral ~0.5."""
        mod = _load_factor_module("money_flow_smart.py")
        closes, highs, lows, volumes = _make_flat_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert abs(result - 0.5) < 0.15, f"Expected ~0.5 for no large volume, got {result}"


class TestVolumePriceConfirmation:
    """Test volume_price_confirmation with known patterns."""

    def test_price_up_volume_up_bullish(self):
        """Price up with increasing volume should score > 0.5."""
        mod = _load_factor_module("money_flow_volume_price_confirmation.py")
        # Consistent price up + volume up
        closes = [10.0 + i * 0.05 for i in range(50)]
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.2 for c in closes]
        volumes = [1000000.0 + i * 50000 for i in range(50)]
        result = mod.compute(closes, highs, lows, volumes, 49)
        assert result > 0.5, f"Expected > 0.5 for price+volume up, got {result}"


class TestLiquidityShock:
    """Test liquidity_shock with volume spike data."""

    def test_volume_spike_detected(self):
        """Volume spike with positive move should give score > 0.5."""
        mod = _load_factor_module("money_flow_liquidity_shock.py")
        closes, highs, lows, volumes = _make_volume_spike_data()
        # Test at idx 82 (2 days after spike at 80)
        result = mod.compute(closes, highs, lows, volumes, 82)
        assert result > 0.5, f"Expected > 0.5 after bullish volume spike, got {result}"

    def test_no_spike_neutral(self):
        """No volume spike should give neutral 0.5."""
        mod = _load_factor_module("money_flow_liquidity_shock.py")
        closes, highs, lows, volumes = _make_flat_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result == 0.5, f"Expected 0.5 for no spike, got {result}"


class TestFearGreedProxy:
    """Test fear_greed_proxy with volatility regimes."""

    def test_low_vol_greed(self):
        """Low volatility (flat data) should give score near 0.0 (greed)."""
        mod = _load_factor_module("regime_fear_greed_proxy.py")
        # Very low volatility: tiny moves
        closes = [10.0 + i * 0.001 for i in range(50)]
        highs = [c + 0.01 for c in closes]
        lows = [c - 0.01 for c in closes]
        volumes = [1000000.0] * 50
        result = mod.compute(closes, highs, lows, volumes, 49)
        assert result < 0.3, f"Expected < 0.3 for low vol (greed), got {result}"

    def test_high_vol_fear(self):
        """High volatility should give score near 1.0 (fear = contrarian buy)."""
        mod = _load_factor_module("regime_fear_greed_proxy.py")
        closes, highs, lows, volumes = _make_volatile_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        # Volatile data should produce higher fear score
        assert result > 0.3, f"Expected > 0.3 for high vol (fear), got {result}"


class TestCapitulationRecovery:
    """Test capitulation_recovery with capitulation pattern."""

    def test_capitulation_pattern_detected(self):
        """Capitulation pattern (red days + increasing volume + reversal) should score > 0.5."""
        mod = _load_factor_module("regime_capitulation_recovery.py")
        closes, highs, lows, volumes = _make_capitulation_data(80)
        # Check at reversal day (index 75)
        result = mod.compute(closes, highs, lows, volumes, 75)
        assert result > 0.5, f"Expected > 0.5 for capitulation recovery, got {result}"

    def test_no_capitulation_neutral(self):
        """Normal uptrend should give neutral ~0.5."""
        mod = _load_factor_module("regime_capitulation_recovery.py")
        closes, highs, lows, volumes = _make_uptrend_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert abs(result - 0.5) < 0.2, f"Expected ~0.5 for no capitulation, got {result}"


class TestEarningsDriftProxy:
    """Test earnings_drift_proxy with gap data."""

    def test_gap_with_continuation(self):
        """Gap up followed by continuation should give score > 0.5."""
        mod = _load_factor_module("regime_earnings_drift_proxy.py")
        closes, highs, lows, volumes = _make_gap_data()
        # Test at idx 75 where continuation from gap at 70 is intact
        result = mod.compute(closes, highs, lows, volumes, 75)
        assert result > 0.5, f"Expected > 0.5 for positive gap with continuation, got {result}"


class TestRelativeStrength:
    """Test relative_strength_vs_market with trend data."""

    def test_strong_uptrend_outperforms(self):
        """Strong uptrend should score > 0.5 (outperforming trend)."""
        mod = _load_factor_module("sector_relative_strength.py")
        # Accelerating uptrend: recent returns > long-term average
        closes = [10.0 + i * 0.02 for i in range(80)]
        # Add acceleration in last 20 days
        for i in range(80, 100):
            closes.append(closes[-1] * 1.015)
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.2 for c in closes]
        volumes = [1000000.0] * len(closes)
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result > 0.5, f"Expected > 0.5 for accelerating uptrend, got {result}"


class TestBreadthThrust:
    """Test breadth_thrust with trend data."""

    def test_strong_uptrend_high_breadth(self):
        """Consistent uptrend should have high breadth (many positive sub-windows)."""
        mod = _load_factor_module("sector_breadth_thrust.py")
        closes, highs, lows, volumes = _make_uptrend_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result > 0.5, f"Expected > 0.5 for consistent uptrend, got {result}"


class TestDispersionSignal:
    """Test dispersion_signal with different data types."""

    def test_volatile_data_high_dispersion(self):
        """Highly volatile data should show high dispersion."""
        mod = _load_factor_module("regime_dispersion_signal.py")
        closes, highs, lows, volumes = _make_volatile_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result > 0.2, f"Expected > 0.2 for volatile data, got {result}"

    def test_flat_data_low_dispersion(self):
        """Flat data should show low dispersion."""
        mod = _load_factor_module("regime_dispersion_signal.py")
        closes, highs, lows, volumes = _make_flat_data()
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result < 0.3, f"Expected < 0.3 for flat data, got {result}"


class TestSectorMomentumRank:
    """Test sector_momentum_rank."""

    def test_accelerating_momentum(self):
        """Accelerating momentum should score > 0.5."""
        mod = _load_factor_module("sector_momentum_rank.py")
        # Slow trend for first 80 days, then clear acceleration in last 5 days
        closes = [10.0 + i * 0.01 for i in range(95)]
        # Last 5 days: much stronger daily gains than the prior 15 days
        for i in range(5):
            closes.append(closes[-1] * 1.03)  # 3% daily for last 5 days
        highs = [c + 0.3 for c in closes]
        lows = [c - 0.2 for c in closes]
        volumes = [1000000.0] * len(closes)
        # Give recent days higher volume for vol_boost
        for i in range(95, 100):
            volumes[i] = 2000000.0
        result = mod.compute(closes, highs, lows, volumes, 99)
        assert result > 0.5, f"Expected > 0.5 for accelerating momentum, got {result}"
