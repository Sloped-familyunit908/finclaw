"""Tests for CryptoTradingBot and DeFiMonitor."""

import pytest
import json
import math
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from crypto.trading_bot import CryptoTradingBot
from defi.defi_monitor import DeFiMonitor


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — RSI Tests
# ═══════════════════════════════════════════════════════════════

class TestRSICalculation:
    """Test RSI calculation with synthetic data."""

    def _make_bot(self):
        """Create a bot with mocked exchange so no real API calls happen."""
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)
        return bot

    def test_rsi_insufficient_data(self):
        bot = self._make_bot()
        assert bot.calculate_rsi([100, 101, 102]) == 50.0

    def test_rsi_all_gains(self):
        bot = self._make_bot()
        prices = [100 + i for i in range(20)]  # monotonically increasing
        rsi = bot.calculate_rsi(prices, period=14)
        assert rsi == 100.0

    def test_rsi_all_losses(self):
        bot = self._make_bot()
        prices = [200 - i for i in range(20)]  # monotonically decreasing
        rsi = bot.calculate_rsi(prices, period=14)
        assert rsi < 5.0  # very low RSI

    def test_rsi_range(self):
        bot = self._make_bot()
        # Alternating: some up, some down
        prices = [100 + (i % 3) * 2 - 2 for i in range(30)]
        rsi = bot.calculate_rsi(prices, period=14)
        assert 0 <= rsi <= 100

    def test_rsi_oversold(self):
        bot = self._make_bot()
        # Strong downtrend then flat
        prices = [100 - i * 0.5 for i in range(20)]
        rsi = bot.calculate_rsi(prices, period=14)
        assert rsi < 30, f"Expected oversold RSI < 30, got {rsi}"

    def test_rsi_overbought(self):
        bot = self._make_bot()
        # Strong uptrend
        prices = [100 + i * 2 for i in range(20)]
        rsi = bot.calculate_rsi(prices, period=14)
        assert rsi > 70, f"Expected overbought RSI > 70, got {rsi}"

    def test_rsi_neutral(self):
        bot = self._make_bot()
        # Roughly flat with tiny oscillation
        import numpy as np
        np.random.seed(42)
        prices = (100 + np.cumsum(np.random.randn(50) * 0.01)).tolist()
        rsi = bot.calculate_rsi(prices, period=14)
        assert 20 < rsi < 80

    def test_rsi_exact_period_plus_one(self):
        bot = self._make_bot()
        # Exactly period+1 data points
        prices = [100 + i for i in range(15)]
        rsi = bot.calculate_rsi(prices, period=14)
        assert rsi == 100.0  # all gains


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — Signal Tests
# ═══════════════════════════════════════════════════════════════

class TestSignalGeneration:
    """Test signal generation with mocked exchange data."""

    def _bot_with_ohlcv(self, closes: list[float]):
        """Create a bot whose exchange.fetch_ohlcv returns synthetic OHLCV."""
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            ohlcv = [[0, 0, 0, 0, c, 0] for c in closes]
            instance.fetch_ohlcv = MagicMock(return_value=ohlcv)
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)
        return bot

    def test_signal_buy(self):
        # Strong downtrend → RSI < 30 → BUY
        closes = [100 - i * 0.5 for i in range(50)]
        bot = self._bot_with_ohlcv(closes)
        sig = bot.get_signal("BTC/USDT")
        assert sig["signal"] in ("buy", "strong_buy")
        assert sig["rsi"] < 30

    def test_signal_sell(self):
        # Strong uptrend → RSI > 70 → SELL
        closes = [100 + i * 2 for i in range(50)]
        bot = self._bot_with_ohlcv(closes)
        sig = bot.get_signal("BTC/USDT")
        assert sig["signal"] in ("sell", "strong_sell")
        assert sig["rsi"] > 70

    def test_signal_hold(self):
        # Flat → RSI ~50 → HOLD
        import numpy as np
        np.random.seed(123)
        closes = (100 + np.cumsum(np.random.randn(50) * 0.01)).tolist()
        bot = self._bot_with_ohlcv(closes)
        sig = bot.get_signal("BTC/USDT")
        assert sig["signal"] == "hold"
        assert 30 <= sig["rsi"] <= 70

    def test_signal_strong_buy(self):
        # Very sharp downtrend  → RSI < 25
        closes = [100 - i * 1.0 for i in range(50)]
        bot = self._bot_with_ohlcv(closes)
        sig = bot.get_signal("BTC/USDT")
        assert sig["signal"] == "strong_buy"
        assert sig["confidence"] == 0.9

    def test_signal_has_required_keys(self):
        closes = [100 + i for i in range(50)]
        bot = self._bot_with_ohlcv(closes)
        sig = bot.get_signal("BTC/USDT")
        for key in ("signal", "rsi", "price", "confidence", "symbol", "timestamp"):
            assert key in sig, f"Missing key: {key}"


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — Trade Execution Tests
# ═══════════════════════════════════════════════════════════════

class TestTradeExecution:
    def _make_bot(self):
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            instance.fetch_ticker = MagicMock(return_value={"last": 50000.0})
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)
        return bot

    def test_simulate_buy(self):
        bot = self._make_bot()
        result = bot.execute_trade("BTC/USDT", "buy", 1000)
        assert result["status"] == "simulated"
        assert result["side"] == "buy"
        assert result["symbol"] == "BTC/USDT"
        assert result["amount"] > 0
        portfolio = bot.get_portfolio()
        assert "BTC" in portfolio
        assert portfolio["BTC"] > 0

    def test_simulate_sell(self):
        bot = self._make_bot()
        # Buy first, then sell
        bot.execute_trade("BTC/USDT", "buy", 1000)
        result = bot.execute_trade("BTC/USDT", "sell", 500)
        assert result["status"] == "simulated"
        assert result["side"] == "sell"

    def test_invalid_side(self):
        bot = self._make_bot()
        with pytest.raises(ValueError, match="side must be"):
            bot.execute_trade("BTC/USDT", "short", 100)

    def test_invalid_amount(self):
        bot = self._make_bot()
        with pytest.raises(ValueError, match="positive"):
            bot.execute_trade("BTC/USDT", "buy", -100)

    def test_portfolio_tracking(self):
        bot = self._make_bot()
        bot.execute_trade("BTC/USDT", "buy", 2000)
        bot.execute_trade("BTC/USDT", "buy", 3000)
        portfolio = bot.get_portfolio()
        assert portfolio["BTC"] == pytest.approx(5000 / 50000, rel=1e-6)


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — Daily Run Tests
# ═══════════════════════════════════════════════════════════════

class TestDailyRun:
    def test_daily_run_returns_list(self):
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            # RSI ~50 → HOLD signal
            import numpy as np
            np.random.seed(99)
            closes = (100 + np.cumsum(np.random.randn(50) * 0.01)).tolist()
            ohlcv = [[0, 0, 0, 0, c, 0] for c in closes]
            instance.fetch_ohlcv = MagicMock(return_value=ohlcv)
            instance.fetch_ticker = MagicMock(return_value={"last": closes[-1]})
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)

        actions = bot.daily_run(symbols=["BTC/USDT"])
        assert len(actions) == 1
        assert "symbol" in actions[0]
        assert "action" in actions[0]

    def test_daily_run_error_handling(self):
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            instance.fetch_ohlcv = MagicMock(side_effect=Exception("network error"))
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)

        actions = bot.daily_run(symbols=["FAIL/USDT"])
        assert len(actions) == 1
        assert actions[0]["action"] == "error"


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — Report Tests
# ═══════════════════════════════════════════════════════════════

class TestReport:
    def test_report_empty(self):
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)
        report = bot.generate_report()
        assert "FinClaw Crypto Trading Report" in report
        assert "binance" in report

    def test_report_after_trades(self):
        with patch("ccxt.binance") as MockExchange:
            instance = MockExchange.return_value
            instance.set_sandbox_mode = MagicMock()
            instance.fetch_ticker = MagicMock(return_value={"last": 3000.0})
            bot = CryptoTradingBot(exchange_id="binance", sandbox=True)
        bot.execute_trade("ETH/USDT", "buy", 600)
        report = bot.generate_report()
        assert "ETH" in report
        assert "BUY" in report


# ═══════════════════════════════════════════════════════════════
# CryptoTradingBot — Constructor Tests
# ═══════════════════════════════════════════════════════════════

class TestBotConstructor:
    def test_unsupported_exchange(self):
        with pytest.raises(ValueError, match="Unsupported exchange"):
            CryptoTradingBot(exchange_id="nonexistent_exchange_xyz")


# ═══════════════════════════════════════════════════════════════
# DeFiMonitor — Tests with mocked API responses
# ═══════════════════════════════════════════════════════════════

MOCK_POOLS_RESPONSE = {
    "status": "success",
    "data": [
        {
            "pool": "pool-1",
            "project": "aave-v3",
            "chain": "Arbitrum",
            "symbol": "USDC-USDT",
            "tvlUsd": 5_000_000,
            "apy": 8.5,
            "apyBase": 3.0,
            "apyReward": 5.5,
        },
        {
            "pool": "pool-2",
            "project": "gmx",
            "chain": "Arbitrum",
            "symbol": "ETH-BTC",
            "tvlUsd": 10_000_000,
            "apy": 15.0,
            "apyBase": 10.0,
            "apyReward": 5.0,
        },
        {
            "pool": "pool-3",
            "project": "uniswap-v3",
            "chain": "Arbitrum",
            "symbol": "WETH-USDC",
            "tvlUsd": 8_000_000,
            "apy": 12.0,
            "apyBase": 12.0,
            "apyReward": 0,
        },
        {
            "pool": "pool-4",
            "project": "curve",
            "chain": "Ethereum",
            "symbol": "DAI-USDC-USDT",
            "tvlUsd": 20_000_000,
            "apy": 4.0,
            "apyBase": 4.0,
            "apyReward": 0,
        },
        {
            "pool": "pool-5",
            "project": "stargate",
            "chain": "Arbitrum",
            "symbol": "USDT",
            "tvlUsd": 3_000_000,
            "apy": 6.0,
            "apyBase": 6.0,
            "apyReward": 0,
        },
        {
            "pool": "pool-6",
            "project": "pendle",
            "chain": "Arbitrum",
            "symbol": "GLP",
            "tvlUsd": 2_000_000,
            "apy": 20.0,
            "apyBase": 8.0,
            "apyReward": 12.0,
        },
        {
            "pool": "pool-7",
            "project": "radiant",
            "chain": "Arbitrum",
            "symbol": "DAI",
            "tvlUsd": 1_500_000,
            "apy": 7.0,
            "apyBase": 3.0,
            "apyReward": 4.0,
        },
    ],
}


MOCK_POOL_HISTORY = {
    "status": "success",
    "data": [
        {"timestamp": "2025-01-01T00:00:00.000Z", "tvlUsd": 5000000, "apy": 8.2},
        {"timestamp": "2025-01-02T00:00:00.000Z", "tvlUsd": 5100000, "apy": 8.5},
        {"timestamp": "2025-01-03T00:00:00.000Z", "tvlUsd": 4900000, "apy": 8.1},
    ],
}


class TestDeFiMonitorTopPools:
    def _make_monitor(self):
        monitor = DeFiMonitor()
        monitor._fetch_pools = MagicMock(return_value=MOCK_POOLS_RESPONSE["data"])
        return monitor

    def test_top_pools_arbitrum(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=1_000_000, min_apy=5.0)
        assert len(pools) > 0
        assert all(p["chain"] == "Arbitrum" for p in pools)
        assert all(p["tvl"] >= 1_000_000 for p in pools)
        assert all(p["apy"] >= 5.0 for p in pools)

    def test_top_pools_sorted_by_apy(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=1_000_000, min_apy=5.0)
        for i in range(len(pools) - 1):
            assert pools[i]["apy"] >= pools[i + 1]["apy"]

    def test_top_pools_limit(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=0, min_apy=0, limit=2)
        assert len(pools) <= 2

    def test_top_pools_no_match(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Solana", min_tvl=1_000_000, min_apy=5.0)
        assert pools == []

    def test_top_pools_high_tvl_filter(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=9_000_000, min_apy=0)
        assert all(p["tvl"] >= 9_000_000 for p in pools)

    def test_top_pools_has_required_keys(self):
        monitor = self._make_monitor()
        pools = monitor.get_top_pools(chain="Arbitrum", min_tvl=0, min_apy=0)
        for p in pools:
            for key in ("pool", "project", "chain", "symbol", "tvl", "apy"):
                assert key in p, f"Missing key: {key}"


class TestDeFiMonitorStablePools:
    def _make_monitor(self):
        monitor = DeFiMonitor()
        monitor._fetch_pools = MagicMock(return_value=MOCK_POOLS_RESPONSE["data"])
        return monitor

    def test_stable_pools_found(self):
        monitor = self._make_monitor()
        pools = monitor.find_best_stable_pools(chain="Arbitrum", min_tvl=500_000)
        assert len(pools) > 0
        # All should have stablecoin=True
        assert all(p["stablecoin"] is True for p in pools)

    def test_stable_pools_sorted(self):
        monitor = self._make_monitor()
        pools = monitor.find_best_stable_pools(chain="Arbitrum")
        for i in range(len(pools) - 1):
            assert pools[i]["apy"] >= pools[i + 1]["apy"]

    def test_stable_pools_no_volatile(self):
        monitor = self._make_monitor()
        pools = monitor.find_best_stable_pools(chain="Arbitrum")
        # GLP and ETH-BTC should NOT appear (not stablecoins)
        symbols = [p["symbol"] for p in pools]
        assert "GLP" not in symbols
        assert "ETH-BTC" not in symbols

    def test_stable_pools_recognizes_usdc(self):
        monitor = self._make_monitor()
        pools = monitor.find_best_stable_pools(chain="Arbitrum", min_tvl=0)
        pool_symbols = [p["symbol"] for p in pools]
        # USDC-USDT and WETH-USDC contain USDC → should appear
        assert any("USDC" in s for s in pool_symbols)


class TestDeFiMonitorPoolHistory:
    def test_pool_history(self):
        monitor = DeFiMonitor()
        monitor._fetch_json = MagicMock(return_value=MOCK_POOL_HISTORY)
        history = monitor.get_pool_history("pool-1")
        assert len(history) == 3
        assert "apy" in history[0]
        assert "tvlUsd" in history[0]


class TestDeFiMonitorRecommendation:
    def _make_monitor(self):
        monitor = DeFiMonitor()
        monitor._fetch_pools = MagicMock(return_value=MOCK_POOLS_RESPONSE["data"])
        return monitor

    def test_recommendation_output(self):
        monitor = self._make_monitor()
        rec = monitor.generate_recommendation(budget_usd=2000)
        assert "FinClaw DeFi Allocation Recommendation" in rec
        assert "Budget: $2,000" in rec
        assert "Conservative" in rec
        assert "Growth" in rec
        assert "⚠️" in rec

    def test_recommendation_custom_budget(self):
        monitor = self._make_monitor()
        rec = monitor.generate_recommendation(budget_usd=5000)
        assert "$5,000" in rec
        # 60% of 5000 = 3000
        assert "$3,000" in rec

    def test_recommendation_contains_apy(self):
        monitor = self._make_monitor()
        rec = monitor.generate_recommendation(budget_usd=1000)
        assert "APY" in rec
        assert "Estimated blended APY" in rec
