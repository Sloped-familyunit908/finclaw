"""Tests for Qlib Alpha158 gap-fill factors."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "factors"))

# ── Test data helpers ────────────────────────────────────────────────

def _make_uptrend(n=60):
    """Generate clearly uptrending data."""
    closes = [100.0 + i * 0.5 for i in range(n)]
    highs  = [c + 1.0 for c in closes]
    lows   = [c - 0.5 for c in closes]
    volumes = [1000000 + i * 10000 for i in range(n)]
    return closes, highs, lows, volumes

def _make_downtrend(n=60):
    """Generate clearly downtrending data."""
    closes = [130.0 - i * 0.5 for i in range(n)]
    highs  = [c + 0.5 for c in closes]
    lows   = [c - 1.0 for c in closes]
    volumes = [1000000 + i * 10000 for i in range(n)]
    return closes, highs, lows, volumes

def _make_flat(n=60):
    """Generate flat/sideways data."""
    closes = [100.0] * n
    highs  = [101.0] * n
    lows   = [99.0] * n
    volumes = [1000000] * n
    return closes, highs, lows, volumes

def _make_volatile(n=60):
    """Generate volatile alternating data."""
    closes  = [100.0 + (2.0 if i % 2 == 0 else -2.0) for i in range(n)]
    highs   = [c + 1.5 for c in closes]
    lows    = [c - 1.5 for c in closes]
    volumes = [1000000 + (500000 if i % 2 == 0 else -300000) for i in range(n)]
    return closes, highs, lows, volumes


# ── 1. KMID tests ────────────────────────────────────────────────────

def test_kmid_uptrend():
    from qlib_kmid import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 30)
    assert 0.5 < score <= 1.0, f"Uptrend KMID should be >0.5, got {score}"

def test_kmid_downtrend():
    from qlib_kmid import compute
    closes, highs, lows, volumes = _make_downtrend()
    score = compute(closes, highs, lows, volumes, 30)
    assert 0.0 <= score < 0.5, f"Downtrend KMID should be <0.5, got {score}"

def test_kmid_edge_idx0():
    from qlib_kmid import compute
    score = compute([100.0], [101.0], [99.0], [1000], 0)
    assert score == 0.5, "KMID at idx=0 should return 0.5"


# ── 2. KSFT tests ────────────────────────────────────────────────────

def test_ksft_close_near_high():
    """When close is near high, KSFT should be > 0.5."""
    from qlib_ksft import compute
    # close near high: 2*close > high + low
    closes = [100.0, 109.0]
    highs  = [101.0, 110.0]
    lows   = [99.0, 100.0]
    volumes = [1000, 1000]
    score = compute(closes, highs, lows, volumes, 1)
    assert 0.5 < score <= 1.0, f"KSFT close-near-high should be >0.5, got {score}"

def test_ksft_flat():
    from qlib_ksft import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 30)
    assert 0.3 <= score <= 0.7, f"Flat KSFT should be near 0.5, got {score}"


# ── 3. SUMP tests ────────────────────────────────────────────────────

def test_sump_uptrend():
    from qlib_sump_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.8, f"Strong uptrend SUMP should be >0.8, got {score}"

def test_sump_downtrend():
    from qlib_sump_20d import compute
    closes, highs, lows, volumes = _make_downtrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score < 0.2, f"Strong downtrend SUMP should be <0.2, got {score}"

def test_sump_edge_short():
    from qlib_sump_20d import compute
    score = compute([100.0] * 5, [101.0] * 5, [99.0] * 5, [1000] * 5, 4)
    assert score == 0.5, "SUMP with insufficient data should return 0.5"


# ── 4. SUMD tests ────────────────────────────────────────────────────

def test_sumd_uptrend():
    from qlib_sumd_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.8, f"Uptrend SUMD should be >0.8, got {score}"

def test_sumd_flat():
    from qlib_sumd_20d import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 40)
    assert score == 0.5, f"Flat SUMD should be 0.5, got {score}"


# ── 5. CNTD tests ────────────────────────────────────────────────────

def test_cntd_uptrend():
    from qlib_cntd_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.8, f"All-up CNTD should be >0.8, got {score}"

def test_cntd_volatile():
    from qlib_cntd_20d import compute
    closes, highs, lows, volumes = _make_volatile()
    score = compute(closes, highs, lows, volumes, 40)
    assert 0.3 <= score <= 0.7, f"Volatile CNTD should be near 0.5, got {score}"


# ── 6. CORD tests ────────────────────────────────────────────────────

def test_cord_edge_short():
    from qlib_cord_20d import compute
    score = compute([100.0] * 5, [101.0] * 5, [99.0] * 5, [1000] * 5, 3)
    assert score == 0.5, "CORD with insufficient data should return 0.5"

def test_cord_returns_valid():
    from qlib_cord_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert 0.0 <= score <= 1.0, f"CORD score out of bounds: {score}"


# ── 7. VMA tests ─────────────────────────────────────────────────────

def test_vma_constant_volume():
    from qlib_vma_20d import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 30)
    assert 0.45 <= score <= 0.55, f"Constant volume VMA should be ~0.5, got {score}"

def test_vma_returns_valid():
    from qlib_vma_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 59)
    assert 0.0 <= score <= 1.0, f"VMA score out of bounds: {score}"


# ── 8. VSTD tests ────────────────────────────────────────────────────

def test_vstd_constant_volume():
    from qlib_vstd_20d import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 30)
    assert score < 0.1, f"Constant volume VSTD should be near 0, got {score}"

def test_vstd_volatile_volume():
    from qlib_vstd_20d import compute
    closes, highs, lows, volumes = _make_volatile()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.0, f"Volatile volume VSTD should be >0, got {score}"


# ── 9. WVMA tests ────────────────────────────────────────────────────

def test_wvma_returns_valid():
    from qlib_wvma_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert 0.0 <= score <= 1.0, f"WVMA score out of bounds: {score}"

def test_wvma_flat():
    from qlib_wvma_20d import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 40)
    assert score == 0.5, f"Flat WVMA should return 0.5 (zero returns), got {score}"


# ── 10. IMXD tests ───────────────────────────────────────────────────

def test_imxd_uptrend():
    """In an uptrend, max comes after min → score > 0.5."""
    from qlib_imxd_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.7, f"Uptrend IMXD should be >0.7 (max after min), got {score}"

def test_imxd_downtrend():
    """In a downtrend, max comes before min → score < 0.5."""
    from qlib_imxd_20d import compute
    closes, highs, lows, volumes = _make_downtrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score < 0.3, f"Downtrend IMXD should be <0.3 (max before min), got {score}"

def test_imxd_edge():
    from qlib_imxd_20d import compute
    score = compute([100.0] * 5, [101.0] * 5, [99.0] * 5, [1000] * 5, 3)
    assert score == 0.5, "IMXD with insufficient data should return 0.5"


# ── 11. RANK tests ───────────────────────────────────────────────────

def test_rank_uptrend():
    """In uptrend, current price is highest → rank near 1.0."""
    from qlib_rank_20d import compute
    closes, highs, lows, volumes = _make_uptrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score > 0.9, f"Uptrend RANK should be near 1.0, got {score}"

def test_rank_downtrend():
    """In downtrend, current price is lowest → rank near 0.0."""
    from qlib_rank_20d import compute
    closes, highs, lows, volumes = _make_downtrend()
    score = compute(closes, highs, lows, volumes, 40)
    assert score < 0.1, f"Downtrend RANK should be near 0.0, got {score}"

def test_rank_flat():
    from qlib_rank_20d import compute
    closes, highs, lows, volumes = _make_flat()
    score = compute(closes, highs, lows, volumes, 30)
    assert score == 0.0, f"Flat RANK (all equal) should be 0.0, got {score}"


# ── Cross-cutting tests ─────────────────────────────────────────────

def test_all_factors_clamp_output():
    """Every factor must return a value in [0, 1]."""
    import importlib
    factor_names = [
        "qlib_kmid", "qlib_ksft", "qlib_sump_20d", "qlib_sumd_20d",
        "qlib_cntd_20d", "qlib_cord_20d", "qlib_vma_20d", "qlib_vstd_20d",
        "qlib_wvma_20d", "qlib_imxd_20d", "qlib_rank_20d",
    ]
    datasets = [_make_uptrend(), _make_downtrend(), _make_flat(), _make_volatile()]

    for name in factor_names:
        mod = importlib.import_module(name)
        for closes, highs, lows, volumes in datasets:
            for test_idx in [0, 1, 10, 30, 59]:
                score = mod.compute(closes, highs, lows, volumes, test_idx)
                assert 0.0 <= score <= 1.0, \
                    f"{name} at idx={test_idx} returned {score} (out of [0,1])"

def test_all_factors_have_metadata():
    """Every factor file must define FACTOR_NAME, FACTOR_DESC, FACTOR_CATEGORY."""
    import importlib
    factor_names = [
        "qlib_kmid", "qlib_ksft", "qlib_sump_20d", "qlib_sumd_20d",
        "qlib_cntd_20d", "qlib_cord_20d", "qlib_vma_20d", "qlib_vstd_20d",
        "qlib_wvma_20d", "qlib_imxd_20d", "qlib_rank_20d",
    ]
    for name in factor_names:
        mod = importlib.import_module(name)
        assert hasattr(mod, "FACTOR_NAME"), f"{name} missing FACTOR_NAME"
        assert hasattr(mod, "FACTOR_DESC"), f"{name} missing FACTOR_DESC"
        assert hasattr(mod, "FACTOR_CATEGORY"), f"{name} missing FACTOR_CATEGORY"
        assert mod.FACTOR_CATEGORY == "qlib_alpha158", \
            f"{name} FACTOR_CATEGORY should be 'qlib_alpha158'"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
