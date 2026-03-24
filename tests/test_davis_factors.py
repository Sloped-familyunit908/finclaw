"""
Tests for Davis Double Play factors.

Tests that all 8 Davis factors:
1. Load correctly into the FactorRegistry
2. Return valid values in [0, 1]
3. Respond correctly to known patterns (bullish/bearish/neutral)
4. Don't crash on edge cases
"""

import math
import random
import pytest

from src.evolution.factor_discovery import FactorRegistry


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def registry():
    reg = FactorRegistry("factors")
    reg.load_all()
    return reg


@pytest.fixture(scope="module")
def davis_factors(registry):
    return {k: v for k, v in registry.factors.items() if k.startswith("davis_")}


def _make_uptrend(n=300, start=10.0, daily_gain=0.005, noise=0.1):
    """Generate clean uptrend data."""
    random.seed(42)
    closes, highs, lows, volumes = [], [], [], []
    price = start
    for i in range(n):
        price *= 1 + daily_gain + random.uniform(-noise * daily_gain, noise * daily_gain)
        h = price * (1 + random.uniform(0, 0.01))
        l = price * (1 - random.uniform(0, 0.01))
        v = 1_000_000 * (1 + i * 0.005)  # Increasing volume
        closes.append(price)
        highs.append(h)
        lows.append(l)
        volumes.append(v)
    return closes, highs, lows, volumes


def _make_downtrend(n=300, start=50.0, daily_loss=0.005):
    """Generate clean downtrend data."""
    random.seed(42)
    closes, highs, lows, volumes = [], [], [], []
    price = start
    for i in range(n):
        price *= 1 - daily_loss + random.uniform(-0.001, 0.001)
        h = price * (1 + random.uniform(0, 0.015))
        l = price * (1 - random.uniform(0, 0.015))
        v = 2_000_000 * (1 - i * 0.003)  # Decreasing volume
        closes.append(price)
        highs.append(max(h, price))
        lows.append(min(l, price))
        volumes.append(max(v, 100_000))
    return closes, highs, lows, volumes


def _make_flat(n=300, price=20.0, noise=0.02):
    """Generate flat/sideways data."""
    random.seed(42)
    closes, highs, lows, volumes = [], [], [], []
    for _ in range(n):
        p = price * (1 + random.uniform(-noise, noise))
        h = p * 1.005
        l = p * 0.995
        v = 500_000
        closes.append(p)
        highs.append(h)
        lows.append(l)
        volumes.append(v)
    return closes, highs, lows, volumes


def _make_acceleration(n=300):
    """Generate accelerating growth — ideal Davis Double Play setup."""
    random.seed(42)
    closes, highs, lows, volumes = [], [], [], []
    price = 10.0
    base_vol = 500_000
    for i in range(n):
        # Accelerating: growth rate increases over time
        growth = 0.001 + (i / n) * 0.01
        price *= 1 + growth + random.uniform(-0.002, 0.002)
        vol = base_vol * (1 + (i / n) * 3)  # Volume also increasing
        h = price * (1 + random.uniform(0, 0.008))
        l = price * (1 - random.uniform(0, 0.005))  # Shallow dips
        closes.append(price)
        highs.append(h)
        lows.append(l)
        volumes.append(vol)
    return closes, highs, lows, volumes


# ── Tests ──────────────────────────────────────────────────────

EXPECTED_DAVIS = {
    "davis_revenue_acceleration",
    "davis_margin_expansion",
    "davis_tech_moat",
    "davis_supply_exhaustion",
    "davis_small_cap_elasticity",
    "davis_volume_price_sync",
    "davis_sector_outperformer",
    "davis_new_demand_catalyst",
}


class TestDavisFactorsLoading:
    """All 8 Davis factors should load and have correct metadata."""

    def test_all_davis_factors_loaded(self, davis_factors):
        loaded_names = set(davis_factors.keys())
        missing = EXPECTED_DAVIS - loaded_names
        assert not missing, f"Missing Davis factors: {missing}"

    def test_all_davis_category(self, davis_factors):
        for name, meta in davis_factors.items():
            assert meta.category == "davis_double_play", (
                f"{name} has category '{meta.category}', expected 'davis_double_play'"
            )

    def test_all_have_descriptions(self, davis_factors):
        for name, meta in davis_factors.items():
            assert len(meta.description) > 10, f"{name} has too short description"


class TestDavisFactorsValueRange:
    """All Davis factors must return values in [0, 1]."""

    @pytest.mark.parametrize("data_fn", [_make_uptrend, _make_downtrend, _make_flat, _make_acceleration])
    def test_value_range(self, davis_factors, data_fn):
        closes, highs, lows, volumes = data_fn()
        for name, meta in davis_factors.items():
            for idx in [60, 100, 150, 200, 250]:
                val = meta.compute_fn(closes, highs, lows, volumes, idx)
                assert 0.0 <= val <= 1.0, (
                    f"{name} returned {val} at idx={idx} with {data_fn.__name__}"
                )

    def test_early_index_returns_neutral(self, davis_factors):
        """Factors should return ~0.5 when not enough data."""
        closes = [10.0] * 30
        highs = [10.5] * 30
        lows = [9.5] * 30
        volumes = [1_000_000] * 30
        for name, meta in davis_factors.items():
            val = meta.compute_fn(closes, highs, lows, volumes, 5)
            assert val == pytest.approx(0.5, abs=0.01), (
                f"{name} returned {val} at idx=5, expected ~0.5"
            )


class TestDavisFactorsDirectionality:
    """Davis factors should score uptrend > flat > downtrend for demand-side factors."""

    def test_uptrend_scores_higher_than_downtrend(self, davis_factors):
        up_c, up_h, up_l, up_v = _make_uptrend()
        dn_c, dn_h, dn_l, dn_v = _make_downtrend()

        # Demand-side factors should clearly prefer uptrend
        demand_factors = [
            "davis_revenue_acceleration",
            "davis_margin_expansion",
            "davis_volume_price_sync",
            "davis_tech_moat",
        ]

        for name in demand_factors:
            if name not in davis_factors:
                continue
            meta = davis_factors[name]
            up_score = meta.compute_fn(up_c, up_h, up_l, up_v, 250)
            dn_score = meta.compute_fn(dn_c, dn_h, dn_l, dn_v, 250)
            assert up_score > dn_score, (
                f"{name}: uptrend score ({up_score:.3f}) should be > "
                f"downtrend score ({dn_score:.3f})"
            )

    def test_acceleration_scores_high(self, davis_factors):
        """Accelerating growth should score very high on demand factors."""
        accel_c, accel_h, accel_l, accel_v = _make_acceleration()

        high_score_factors = [
            "davis_revenue_acceleration",
            "davis_tech_moat",
        ]

        for name in high_score_factors:
            if name not in davis_factors:
                continue
            meta = davis_factors[name]
            score = meta.compute_fn(accel_c, accel_h, accel_l, accel_v, 250)
            assert score > 0.65, (
                f"{name}: acceleration data should score > 0.65, got {score:.3f}"
            )

    def test_supply_exhaustion_prefers_bottom(self, davis_factors):
        """Supply exhaustion factor should score higher after a decline + flat base."""
        # Build: 60 days of decline, then 60 days of flat base
        random.seed(42)
        closes, highs, lows, volumes = [], [], [], []
        price = 50.0

        # Decline phase
        for i in range(120):
            price *= 0.995 + random.uniform(-0.002, 0.002)
            h = price * 1.01
            l = price * 0.99
            v = 2_000_000 * (1 - i * 0.005)
            closes.append(price)
            highs.append(h)
            lows.append(l)
            volumes.append(max(v, 200_000))

        # Base phase (flat, low volume)
        base_price = price
        for i in range(120):
            price = base_price * (1 + random.uniform(-0.01, 0.012))
            h = price * 1.005
            l = price * 0.995
            v = 300_000
            closes.append(price)
            highs.append(h)
            lows.append(l)
            volumes.append(v)

        if "davis_supply_exhaustion" in davis_factors:
            meta = davis_factors["davis_supply_exhaustion"]
            score = meta.compute_fn(closes, highs, lows, volumes, 200)
            assert score > 0.55, (
                f"Supply exhaustion should score > 0.55 after decline+base, got {score:.3f}"
            )


class TestDavisFactorsEdgeCases:
    """Edge cases that shouldn't crash."""

    def test_zero_volume(self, davis_factors):
        closes = [10.0 + i * 0.01 for i in range(100)]
        highs = [c + 0.1 for c in closes]
        lows = [c - 0.1 for c in closes]
        volumes = [0] * 100

        for name, meta in davis_factors.items():
            val = meta.compute_fn(closes, highs, lows, volumes, 80)
            assert 0.0 <= val <= 1.0, f"{name} crashed on zero volume"

    def test_constant_price(self, davis_factors):
        closes = [20.0] * 200
        highs = [20.0] * 200
        lows = [20.0] * 200
        volumes = [1_000_000] * 200

        for name, meta in davis_factors.items():
            val = meta.compute_fn(closes, highs, lows, volumes, 150)
            assert 0.0 <= val <= 1.0, f"{name} crashed on constant price"

    def test_single_spike(self, davis_factors):
        """A single day spike shouldn't give high scores on sustained factors."""
        closes = [10.0] * 200
        highs = [10.5] * 200
        lows = [9.5] * 200
        volumes = [500_000] * 200

        # Single spike day
        closes[190] = 15.0
        highs[190] = 16.0
        volumes[190] = 5_000_000

        for name in ["davis_volume_price_sync", "davis_margin_expansion"]:
            if name not in davis_factors:
                continue
            meta = davis_factors[name]
            val = meta.compute_fn(closes, highs, lows, volumes, 195)
            assert val < 0.75, (
                f"{name} should not score high on a single spike, got {val:.3f}"
            )
