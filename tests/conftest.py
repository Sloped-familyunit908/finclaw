"""Shared fixtures for FinClaw test suite."""
import sys
import os
import math
import random

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_prices(start=100.0, n=300, trend=0.0003, volatility=0.02, seed=42):
    """Generate synthetic price series for testing."""
    rng = random.Random(seed)
    prices = [start]
    for _ in range(n - 1):
        ret = trend + volatility * rng.gauss(0, 1)
        prices.append(prices[-1] * (1 + ret))
    return prices


def make_bull_prices(n=300, seed=42):
    return make_prices(100, n, trend=0.001, volatility=0.015, seed=seed)


def make_bear_prices(n=300, seed=42):
    return make_prices(100, n, trend=-0.001, volatility=0.02, seed=seed)


def make_crash_prices(n=300, seed=42):
    """Start normal, then crash 40% mid-series."""
    prices = make_prices(100, n // 2, trend=0.0005, volatility=0.015, seed=seed)
    crash_start = prices[-1]
    rng = random.Random(seed + 1)
    for i in range(n - n // 2):
        drop = -0.005 - 0.03 * (i < 30)
        prices.append(prices[-1] * (1 + drop + 0.02 * rng.gauss(0, 1)))
    return prices


def make_ranging_prices(n=300, seed=42):
    return make_prices(100, n, trend=0.0, volatility=0.015, seed=seed)


def make_volatile_prices(n=300, seed=42):
    return make_prices(100, n, trend=0.0002, volatility=0.04, seed=seed)


def make_history(prices):
    """Convert price list to history dicts (as expected by backtester)."""
    from datetime import datetime, timedelta
    base = datetime(2020, 1, 1)
    return [
        {"date": base + timedelta(days=i), "price": p, "volume": 1000000}
        for i, p in enumerate(prices)
    ]
