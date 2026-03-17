"""Tests for BTC on-chain metrics, funding dashboard, liquidation tracker, lightning monitor, and BTC cycle strategy."""

import time
from unittest.mock import patch, MagicMock

import pytest

# ── BTC Metrics ──────────────────────────────────────────────────

from src.crypto.btc_metrics import (
    BTCMetricsClient, BTCOnChainMetrics, FearGreedIndex, MVRVData, MinerOutflow,
    _classify_fear_greed,
)


class TestClassifyFearGreed:
    def test_extreme_fear(self):
        assert _classify_fear_greed(10) == "Extreme Fear"

    def test_fear(self):
        assert _classify_fear_greed(35) == "Fear"

    def test_neutral(self):
        assert _classify_fear_greed(50) == "Neutral"

    def test_greed(self):
        assert _classify_fear_greed(70) == "Greed"

    def test_extreme_greed(self):
        assert _classify_fear_greed(90) == "Extreme Greed"


class TestBTCMetricsClient:
    def setup_method(self):
        self.client = BTCMetricsClient(timeout=5)

    def test_get_onchain_metrics_success(self):
        """Test successful API response parsing."""
        mock_bc = MagicMock()
        mock_bc.get.return_value = {
            "hash_rate": 600_000_000,
            "difficulty": 80_000_000_000_000,
            "n_tx": 50000,
            "minutes_between_blocks": 9.5,
            "trade_volume_usd": 150000,
        }
        self.client._blockchain_client = mock_bc
        result = self.client.get_onchain_metrics()
        assert isinstance(result, BTCOnChainMetrics)
        assert result.hashrate == 600_000_000
        assert result.difficulty == 80_000_000_000_000
        assert result.mempool_size == 50000
        assert result.avg_block_time == 9.5

    def test_get_onchain_metrics_fallback(self):
        """Test fallback to simulated data on connection error."""
        with patch.object(self.client, '_blockchain_client') as mock:
            from src.exchanges.http_client import ExchangeConnectionError
            mock.get.side_effect = ExchangeConnectionError("timeout", "https://api.blockchain.info")
            result = self.client.get_onchain_metrics()
            assert isinstance(result, BTCOnChainMetrics)
            assert result.hashrate > 0

    def test_get_fear_greed_success(self):
        mock_alt = MagicMock()
        mock_alt.get.return_value = {
            "data": [{"value": "25", "value_classification": "Extreme Fear", "timestamp": "1700000000"}]
        }
        self.client._alt_me_client = mock_alt
        result = self.client.get_fear_greed(limit=1)
        assert len(result) == 1
        assert result[0].value == 25
        assert result[0].label == "Extreme Fear"

    def test_get_fear_greed_fallback(self):
        with patch.object(self.client, '_alt_me_client') as mock:
            mock.get.side_effect = Exception("network error")
            result = self.client.get_fear_greed()
            assert len(result) == 1
            assert isinstance(result[0], FearGreedIndex)

    def test_get_mvrv_ratio_fallback(self):
        with patch.object(self.client, '_blockchain_client') as mock:
            mock.get.side_effect = Exception("fail")
            result = self.client.get_mvrv_ratio()
            assert isinstance(result, MVRVData)
            assert result.mvrv_ratio > 0
            assert result.signal in ("undervalued", "fair", "overvalued")

    def test_get_miner_outflow(self):
        result = self.client.get_miner_outflow()
        assert isinstance(result, MinerOutflow)
        assert result.daily_outflow_btc > 0
        assert result.outflow_trend in ("increasing", "stable", "decreasing")
        assert result.signal in ("bearish", "bullish", "neutral")

    def test_mvrv_signal_thresholds(self):
        assert BTCMetricsClient._mvrv_signal(0.5) == "undervalued"
        assert BTCMetricsClient._mvrv_signal(1.5) == "fair"
        assert BTCMetricsClient._mvrv_signal(3.5) == "overvalued"


# ── Funding Dashboard ─────────────────────────────────────────────

from src.crypto.funding_dashboard import (
    FundingDashboardClient, FundingRate, FundingArbitrage, FundingDashboard,
    _annualize_8h_rate,
)


class TestAnnualizeRate:
    def test_positive_rate(self):
        result = _annualize_8h_rate(0.0001)
        assert result == round(0.0001 * 3 * 365 * 100, 4)

    def test_zero_rate(self):
        assert _annualize_8h_rate(0) == 0

    def test_negative_rate(self):
        result = _annualize_8h_rate(-0.0001)
        assert result < 0


class TestFundingDashboardClient:
    def setup_method(self):
        self.client = FundingDashboardClient(timeout=5)

    def test_find_arbitrage_with_spread(self):
        rates = [
            FundingRate(exchange="binance", symbol="BTCUSDT", rate=0.0001, annualized=10.95),
            FundingRate(exchange="bybit", symbol="BTCUSDT", rate=-0.0001, annualized=-10.95),
            FundingRate(exchange="okx", symbol="BTCUSDT", rate=0.00005, annualized=5.475),
        ]
        arbs = self.client.find_arbitrage(rates, min_spread=5.0)
        assert len(arbs) >= 1
        top = arbs[0]
        assert top.symbol == "BTCUSDT"
        assert top.long_exchange == "bybit"  # lowest rate
        assert top.short_exchange == "binance"  # highest rate
        assert top.spread > 5.0

    def test_find_arbitrage_no_spread(self):
        rates = [
            FundingRate(exchange="binance", symbol="BTCUSDT", rate=0.0001, annualized=10.95),
            FundingRate(exchange="bybit", symbol="BTCUSDT", rate=0.00009, annualized=9.855),
        ]
        arbs = self.client.find_arbitrage(rates, min_spread=50.0)
        assert len(arbs) == 0

    def test_get_all_rates_fallback(self):
        """All exchanges fail → get simulated rates."""
        with patch.object(self.client, '_binance') as mb, \
             patch.object(self.client, '_bybit') as mby, \
             patch.object(self.client, '_okx') as mokx:
            mb.get.side_effect = Exception("fail")
            mby.get.side_effect = Exception("fail")
            mokx.get.side_effect = Exception("fail")
            rates = self.client.get_all_rates(["BTCUSDT"])
            assert len(rates) >= 3  # one per exchange

    def test_get_dashboard(self):
        with patch.object(self.client, 'get_all_rates') as mock:
            mock.return_value = [
                FundingRate(exchange="binance", symbol="BTCUSDT", rate=0.0003, annualized=32.85),
                FundingRate(exchange="bybit", symbol="BTCUSDT", rate=-0.0001, annualized=-10.95),
            ]
            dashboard = self.client.get_dashboard(["BTCUSDT"])
            assert isinstance(dashboard, FundingDashboard)
            assert len(dashboard.rates) == 2

    def test_fetch_binance_success(self):
        with patch.object(self.client, '_binance') as mock:
            mock.get.return_value = [
                {"symbol": "BTCUSDT", "lastFundingRate": "0.0001", "nextFundingTime": 1700000000}
            ]
            rates = self.client._fetch_binance(["BTCUSDT"])
            assert len(rates) == 1
            assert rates[0].exchange == "binance"

    def test_fetch_bybit_success(self):
        with patch.object(self.client, '_bybit') as mock:
            mock.get.return_value = {"result": {"list": [{"fundingRate": "0.00015"}]}}
            rates = self.client._fetch_bybit(["BTCUSDT"])
            assert len(rates) == 1
            assert rates[0].exchange == "bybit"


# ── Liquidation Tracker ──────────────────────────────────────────

from src.crypto.liquidation_tracker import (
    LiquidationTracker, LiquidationEvent, LiquidationSummary, LiquidationHeatmapLevel,
)


class TestLiquidationTracker:
    def setup_method(self):
        self.tracker = LiquidationTracker(timeout=5, alert_threshold_usd=1_000_000)

    def test_simulated_liquidations(self):
        events = LiquidationTracker._simulated_liquidations("binance", "BTCUSDT")
        assert len(events) == 20
        for e in events:
            assert e.exchange == "binance"
            assert e.symbol == "BTCUSDT"
            assert e.side in ("long", "short")
            assert e.usd_value > 0

    def test_get_recent_liquidations_fallback(self):
        with patch.object(self.tracker, '_binance') as mb, \
             patch.object(self.tracker, '_bybit') as mby:
            mb.get.side_effect = Exception("fail")
            mby.get.side_effect = Exception("fail")
            events = self.tracker.get_recent_liquidations("BTCUSDT")
            assert len(events) == 40  # 20 per exchange
            # sorted by timestamp desc
            for i in range(len(events) - 1):
                assert events[i].timestamp >= events[i + 1].timestamp

    def test_get_summary(self):
        with patch.object(self.tracker, 'get_recent_liquidations') as mock:
            mock.return_value = [
                LiquidationEvent("binance", "BTCUSDT", "long", 1.0, 65000, 65000, int(time.time())),
                LiquidationEvent("bybit", "BTCUSDT", "short", 0.5, 64500, 32250, int(time.time()) - 60),
            ]
            summary = self.tracker.get_summary("BTCUSDT")
            assert isinstance(summary, LiquidationSummary)
            assert summary.total_long_liquidations_usd == 65000
            assert summary.total_short_liquidations_usd == 32250
            assert summary.largest_single_usd == 65000
            assert len(summary.heatmap) > 0

    def test_build_heatmap(self):
        events = [
            LiquidationEvent("binance", "BTCUSDT", "long", 1.0, 65100, 65100, 0),
            LiquidationEvent("binance", "BTCUSDT", "short", 0.5, 65200, 32600, 0),
            LiquidationEvent("bybit", "BTCUSDT", "long", 2.0, 66000, 132000, 0),
        ]
        heatmap = self.tracker._build_heatmap(events, price_step=500)
        assert len(heatmap) >= 1
        for level in heatmap:
            assert isinstance(level, LiquidationHeatmapLevel)
            assert level.total_usd == level.long_liquidations_usd + level.short_liquidations_usd

    def test_check_alerts_large_volume(self):
        events = [
            LiquidationEvent("binance", "BTCUSDT", "long", 10, 65000, 650000, 0),
            LiquidationEvent("binance", "BTCUSDT", "short", 10, 65000, 650000, 0),
        ]
        heatmap = self.tracker._build_heatmap(events, 500)
        alerts = self.tracker._check_alerts(events, heatmap)
        assert len(alerts) >= 1  # total > threshold


# ── Lightning Monitor ────────────────────────────────────────────

from src.crypto.lightning import LightningMonitor, LightningStats, LightningNode


class TestLightningMonitor:
    def setup_method(self):
        self.monitor = LightningMonitor(timeout=5)

    def test_get_network_stats_fallback(self):
        with patch.object(self.monitor, '_client') as mock:
            mock.get.side_effect = Exception("fail")
            stats = self.monitor.get_network_stats()
            assert isinstance(stats, LightningStats)
            assert stats.capacity_btc > 0
            assert stats.node_count > 0
            assert stats.channel_count > 0

    def test_get_network_stats_success(self):
        with patch.object(self.monitor, '_client') as mock:
            mock.get.return_value = {
                "latest": {
                    "total_capacity": {"value": 520000000000},
                    "node_count": {"value": 16500},
                    "channel_count": {"value": 52000},
                    "avg_fee_rate": {"value": 150},
                    "avg_base_fee": {"value": 1000},
                }
            }
            stats = self.monitor.get_network_stats()
            assert stats.capacity_btc == 5200.0
            assert stats.node_count == 16500

    def test_get_top_nodes_fallback(self):
        with patch.object(self.monitor, '_client') as mock:
            mock.get.side_effect = Exception("fail")
            nodes = self.monitor.get_top_nodes(limit=5)
            assert len(nodes) == 5
            for n in nodes:
                assert isinstance(n, LightningNode)
                assert n.capacity_btc > 0

    def test_get_top_nodes_success(self):
        with patch.object(self.monitor, '_client') as mock:
            mock.get.return_value = [
                {"alias": "ACINQ", "pub_key": "abc123", "capacity": 50000000000, "channelcount": 500},
                {"alias": "Bitfinex", "pub_key": "def456", "capacity": 30000000000, "channelcount": 300},
            ]
            nodes = self.monitor.get_top_nodes(limit=2)
            assert len(nodes) == 2
            assert nodes[0].alias == "ACINQ"

    def test_simulated_top_nodes_sorted(self):
        nodes = LightningMonitor._simulated_top_nodes(10)
        for i in range(len(nodes) - 1):
            assert nodes[i].capacity_btc >= nodes[i + 1].capacity_btc


# ── BTC Cycle Strategy ──────────────────────────────────────────

from src.strategies.library.btc_cycle import BTCCycleIndicator
from src.strategies.library.base import StrategySignal, StrategyMeta


class TestBTCCycleIndicator:
    def setup_method(self):
        self.strategy = BTCCycleIndicator()

    def test_meta(self):
        m = BTCCycleIndicator.meta()
        assert isinstance(m, StrategyMeta)
        assert m.slug == "btc-cycle"
        assert m.category == "crypto"

    def test_buy_signal_all_extreme_fear(self):
        """All 3 indicators at buy thresholds → BUY."""
        data = []
        # Need enough bars for hashrate SMA (60 bars)
        for i in range(70):
            if i < 60:
                # Normal data - hashrate declining
                data.append({
                    "close": 30000,
                    "fear_greed": 50,
                    "mvrv": 1.5,
                    "hashrate": 600 - i * 5,  # declining
                })
            else:
                # Extreme fear zone with low hashrate
                data.append({
                    "close": 20000,
                    "fear_greed": 15,
                    "mvrv": 0.8,
                    "hashrate": 300,  # low, below SMA
                })
        signals = self.strategy.generate_signals(data)
        assert len(signals) == 70
        # Last signals should be buy
        buy_signals = [s for s in signals[-5:] if s.action == "buy"]
        assert len(buy_signals) > 0

    def test_sell_signal_all_extreme_greed(self):
        """All 3 indicators at sell thresholds → SELL."""
        data = []
        for i in range(70):
            if i < 60:
                data.append({
                    "close": 60000,
                    "fear_greed": 50,
                    "mvrv": 1.5,
                    "hashrate": 400 + i * 5,  # increasing
                })
            else:
                data.append({
                    "close": 100000,
                    "fear_greed": 85,
                    "mvrv": 3.5,
                    "hashrate": 800,  # high, above SMA * 1.1
                })
        signals = self.strategy.generate_signals(data)
        sell_signals = [s for s in signals[-5:] if s.action == "sell"]
        assert len(sell_signals) > 0

    def test_hold_when_mixed(self):
        """Mixed indicators → HOLD."""
        data = [{"close": 50000, "fear_greed": 50, "mvrv": 1.5, "hashrate": 500} for _ in range(70)]
        signals = self.strategy.generate_signals(data)
        assert all(s.action == "hold" for s in signals)

    def test_backtest_runs(self):
        """Strategy backtest should not error."""
        data = [{"close": 50000 + i * 100, "open": 50000 + i * 100,
                 "high": 50200 + i * 100, "low": 49800 + i * 100,
                 "volume": 1000, "fear_greed": 50, "mvrv": 1.5,
                 "hashrate": 500} for i in range(100)]
        result = self.strategy.backtest(data)
        assert "total_return" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result

    def test_custom_thresholds(self):
        """Custom thresholds work."""
        strat = BTCCycleIndicator(fear_greed_buy=30, fear_greed_sell=70, mvrv_buy=0.8, mvrv_sell=2.5)
        assert strat.fear_greed_buy == 30
        assert strat.mvrv_sell == 2.5


# ── Strategy Registry ───────────────────────────────────────────

class TestStrategyRegistry:
    def test_btc_cycle_registered(self):
        from src.strategies.library import STRATEGY_REGISTRY, get_strategy
        assert "btc-cycle" in STRATEGY_REGISTRY
        cls = get_strategy("btc-cycle")
        assert cls is BTCCycleIndicator
