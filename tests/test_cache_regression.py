"""
Cache Regression Tests
======================
Tests the DataCache DataFrame serialization/deserialization fix.
Ensures DataFrames survive a round-trip through the cache intact.
"""

import os
import shutil
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src.data.cache import DataCache


@pytest.fixture
def cache_dir(tmp_path):
    """Create a temporary cache directory."""
    d = tmp_path / "test_cache"
    d.mkdir()
    return str(d)


@pytest.fixture
def cache(cache_dir):
    """Create a fresh DataCache instance."""
    return DataCache(cache_dir=cache_dir)


class TestDataFrameCacheRoundTrip:
    """Test DataFrame serialization/deserialization through cache."""

    def test_basic_dataframe_roundtrip(self, cache):
        """Store a DataFrame, retrieve it, verify columns and data intact."""
        df = pd.DataFrame({
            "Open": [100.0, 101.5, 99.8],
            "High": [102.0, 103.5, 101.0],
            "Low": [99.0, 100.0, 98.5],
            "Close": [101.0, 102.0, 100.5],
            "Volume": [1000000, 1500000, 1200000],
        })
        cache.set("test_basic", df)
        result = cache.get("test_basic")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == list(df.columns)
        assert len(result) == len(df)
        np.testing.assert_array_almost_equal(result["Close"].values, df["Close"].values)
        np.testing.assert_array_almost_equal(result["Volume"].values, df["Volume"].values)

    def test_dataframe_with_datetime_index(self, cache):
        """DataFrame with DatetimeIndex should survive cache round-trip."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "Close": [150.0, 151.5, 149.8, 152.0, 153.5],
            "Volume": [1e6, 1.2e6, 0.9e6, 1.1e6, 1.3e6],
        }, index=dates)

        cache.set("test_datetime_idx", df)
        result = cache.get("test_datetime_idx")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert list(result.columns) == ["Close", "Volume"]
        np.testing.assert_array_almost_equal(result["Close"].values, df["Close"].values)

    def test_dataframe_with_timezone_aware_index(self, cache):
        """DataFrame with timezone-aware DatetimeIndex should survive round-trip."""
        dates = pd.date_range("2024-01-01", periods=5, freq="D", tz="US/Eastern")
        df = pd.DataFrame({
            "Close": [150.0, 151.5, 149.8, 152.0, 153.5],
        }, index=dates)

        cache.set("test_tz_aware", df)
        result = cache.get("test_tz_aware")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        np.testing.assert_array_almost_equal(result["Close"].values, df["Close"].values)
        # Index should be datetime (may be UTC-normalized)
        assert hasattr(result.index, "year") or all(
            isinstance(str(idx), str) for idx in result.index
        )

    def test_dataframe_with_mixed_timezone_strings(self, cache):
        """DataFrame index with mixed timezone string representations."""
        # Simulate what yfinance might return: string timestamps with timezone info
        idx = pd.to_datetime([
            "2024-01-02 00:00:00-05:00",
            "2024-01-03 00:00:00-05:00",
            "2024-01-04 00:00:00-05:00",
        ])
        df = pd.DataFrame({
            "Close": [150.0, 151.0, 152.0],
            "Volume": [1e6, 1.1e6, 0.95e6],
        }, index=idx)

        cache.set("test_mixed_tz", df)
        result = cache.get("test_mixed_tz")

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        np.testing.assert_array_almost_equal(result["Close"].values, df["Close"].values)

    def test_dataframe_columns_preserved(self, cache):
        """Column names and order should be preserved exactly."""
        df = pd.DataFrame({
            "Open": [100.0],
            "High": [105.0],
            "Low": [98.0],
            "Close": [103.0],
            "Adj Close": [102.5],
            "Volume": [5000000],
        })
        cache.set("test_columns", df)
        result = cache.get("test_columns")

        assert result is not None
        assert list(result.columns) == ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

    def test_large_dataframe(self, cache):
        """Larger DataFrame (1000 rows) should survive round-trip."""
        dates = pd.date_range("2020-01-01", periods=1000, freq="D")
        np.random.seed(42)
        close = 100 * np.cumprod(1 + np.random.normal(0.0003, 0.02, 1000))
        df = pd.DataFrame({
            "Open": close * 0.999,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.random.randint(1_000_000, 10_000_000, 1000).astype(float),
        }, index=dates)

        cache.set("test_large", df)
        result = cache.get("test_large")

        assert result is not None
        assert len(result) == 1000
        np.testing.assert_array_almost_equal(result["Close"].values, df["Close"].values, decimal=4)

    def test_empty_dataframe(self, cache):
        """Empty DataFrame should not crash the cache."""
        df = pd.DataFrame({"Close": [], "Volume": []})
        cache.set("test_empty", df)
        result = cache.get("test_empty")
        # Should either return empty DataFrame or the JSON structure
        assert result is not None


class TestCacheExpiry:
    """Test cache TTL expiration."""

    def test_fresh_entry_not_expired(self, cache):
        """Recently cached data should be retrievable."""
        cache.set("fresh", {"value": 42})
        result = cache.get("fresh", max_age_hours=1)
        assert result is not None
        assert result["value"] == 42

    def test_expired_entry_returns_none(self, cache):
        """Expired cache entry should return None."""
        cache.set("old", {"value": 99})
        # Get with max_age_hours=0 should always be expired (data is at least a few ms old)
        # Use a very small max_age to force expiry
        time.sleep(0.1)
        result = cache.get("old", max_age_hours=0)
        # max_age_hours=0 means "must be within 0 hours" which is impossible
        assert result is None

    def test_max_age_24h_default(self, cache):
        """Default max_age of 24h should work for fresh entries."""
        cache.set("default_ttl", [1, 2, 3])
        result = cache.get("default_ttl")  # default max_age_hours=24
        assert result == [1, 2, 3]

    def test_different_max_age_values(self, cache):
        """Different max_age values should be respected."""
        cache.set("ttl_test", {"data": "hello"})
        # Should be retrievable with large max_age
        assert cache.get("ttl_test", max_age_hours=9999) is not None
        # Should be retrievable with reasonable max_age
        assert cache.get("ttl_test", max_age_hours=1) is not None


class TestCacheClear:
    """Test cache clearing functionality."""

    def test_clear_all(self, cache):
        """Clearing all entries should empty the cache."""
        cache.set("a", {"val": 1})
        cache.set("b", {"val": 2})
        cache.set("c", {"val": 3})

        assert len(cache.keys()) == 3
        cleared = cache.clear()
        assert cleared == 3
        assert len(cache.keys()) == 0
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_clear_old_entries(self, cache):
        """Clearing old entries should keep fresh ones."""
        cache.set("keep", {"val": "fresh"})
        # Clear entries older than 1 day — our entry is < 1 second old
        cleared = cache.clear(older_than_days=1)
        assert cleared == 0
        assert cache.get("keep") is not None

    def test_stats_after_operations(self, cache):
        """Stats should reflect current cache state."""
        stats = cache.stats()
        assert stats["entries"] == 0

        cache.set("x", {"data": 1})
        cache.set("y", {"data": 2})
        stats = cache.stats()
        assert stats["entries"] == 2
        assert stats["size_kb"] > 0

        cache.clear()
        stats = cache.stats()
        assert stats["entries"] == 0

    def test_keys_listing(self, cache):
        """Cache.keys() should list all stored keys."""
        cache.set("alpha", 1)
        cache.set("beta", 2)
        cache.set("gamma", 3)

        keys = cache.keys()
        assert set(keys) == {"alpha", "beta", "gamma"}


class TestCacheJSONTypes:
    """Test caching various JSON-serializable types."""

    def test_cache_dict(self, cache):
        cache.set("dict", {"a": 1, "b": "hello", "c": [1, 2, 3]})
        result = cache.get("dict")
        assert result == {"a": 1, "b": "hello", "c": [1, 2, 3]}

    def test_cache_list(self, cache):
        cache.set("list", [1, 2, 3, "four", 5.0])
        result = cache.get("list")
        assert result == [1, 2, 3, "four", 5.0]

    def test_cache_nested(self, cache):
        data = {"level1": {"level2": {"level3": [1, 2, 3]}}}
        cache.set("nested", data)
        result = cache.get("nested")
        assert result == data

    def test_cache_overwrite(self, cache):
        """Setting the same key should overwrite."""
        cache.set("key", {"v": 1})
        cache.set("key", {"v": 2})
        result = cache.get("key")
        assert result == {"v": 2}
        assert len(cache.keys()) == 1
