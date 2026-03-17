"""Tests for DeFi Llama integration and enhanced yield tracker."""

import json
import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from defi.defillama import DefiLlamaClient, ProtocolInfo, YieldPool, ChainTVL, StablecoinInfo


# ── Sample API responses ──────────────────────────────────────────

SAMPLE_PROTOCOLS = json.dumps([
    {"name": "Lido", "slug": "lido", "tvl": 15_000_000_000, "chain": "Ethereum",
     "chains": ["Ethereum"], "category": "Liquid Staking", "change_1d": 1.2, "change_7d": -0.5},
    {"name": "Aave", "slug": "aave-v3", "tvl": 10_000_000_000, "chain": "Multi-Chain",
     "chains": ["Ethereum", "Polygon"], "category": "Lending", "change_1d": 0.5, "change_7d": 2.1},
    {"name": "Uniswap", "slug": "uniswap", "tvl": 5_000_000_000, "chain": "Ethereum",
     "chains": ["Ethereum"], "category": "DEX", "change_1d": None, "change_7d": None},
]).encode()

SAMPLE_YIELDS = json.dumps({"data": [
    {"pool": "pool-1", "project": "aave-v3", "chain": "Ethereum", "symbol": "USDC",
     "tvlUsd": 2_000_000_000, "apy": 4.5, "apyBase": 3.0, "apyReward": 1.5},
    {"pool": "pool-2", "project": "compound", "chain": "Ethereum", "symbol": "ETH",
     "tvlUsd": 500_000, "apy": 2.1, "apyBase": 2.1, "apyReward": None},
    {"pool": "pool-3", "project": "pancakeswap", "chain": "BSC", "symbol": "CAKE-BNB",
     "tvlUsd": 50_000, "apy": 25.0, "apyBase": 25.0, "apyReward": None},  # below min_tvl
    {"pool": "pool-4", "project": "curve", "chain": "Ethereum", "symbol": "3pool",
     "tvlUsd": 3_000_000_000, "apy": 6.2, "apyBase": 6.2, "apyReward": None},
    {"pool": "pool-zero", "project": "dead", "chain": "Ethereum", "symbol": "X",
     "tvlUsd": 1_000_000, "apy": 0, "apyBase": 0, "apyReward": None},  # zero APY
]}).encode()

SAMPLE_CHAINS = json.dumps([
    {"name": "Ethereum", "tvl": 50_000_000_000},
    {"name": "BSC", "tvl": 5_000_000_000},
    {"name": "Solana", "tvl": 3_000_000_000},
]).encode()

SAMPLE_STABLECOINS = json.dumps({"peggedAssets": [
    {"name": "Tether", "symbol": "USDT", "pegType": "peggedUSD",
     "circulating": {"peggedUSD": 80_000_000_000}, "price": 1.0},
    {"name": "USD Coin", "symbol": "USDC", "pegType": "peggedUSD",
     "circulating": {"peggedUSD": 30_000_000_000}, "price": 1.0},
    {"name": "DAI", "symbol": "DAI", "pegType": "peggedUSD",
     "circulating": {"peggedUSD": 5_000_000_000}, "price": 0.9998},
]}).encode()


def _mock_urlopen(response_bytes):
    """Create a mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestDefiLlamaClient:

    @patch("urllib.request.urlopen")
    def test_get_top_protocols(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_PROTOCOLS)
        client = DefiLlamaClient()
        protocols = client.get_top_protocols(limit=2)
        assert len(protocols) == 2
        assert protocols[0].name == "Lido"
        assert protocols[0].tvl == 15_000_000_000
        assert protocols[1].category == "Lending"

    @patch("urllib.request.urlopen")
    def test_get_top_protocols_change_fields(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_PROTOCOLS)
        client = DefiLlamaClient()
        protocols = client.get_top_protocols(limit=3)
        assert protocols[0].change_1d == 1.2
        assert protocols[2].change_1d is None  # Uniswap

    @patch("urllib.request.urlopen")
    def test_get_best_yields(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_YIELDS)
        client = DefiLlamaClient()
        pools = client.get_best_yields(min_tvl=100_000)
        # Should exclude pool-3 (tvl < 100k) and pool-zero (apy == 0)
        assert len(pools) == 3
        # Sorted by APY desc
        assert pools[0].apy >= pools[1].apy >= pools[2].apy

    @patch("urllib.request.urlopen")
    def test_get_best_yields_chain_filter(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_YIELDS)
        client = DefiLlamaClient()
        pools = client.get_best_yields(chain="Ethereum", min_tvl=100_000)
        assert all(p.chain == "Ethereum" for p in pools)

    @patch("urllib.request.urlopen")
    def test_get_chain_rankings(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_CHAINS)
        client = DefiLlamaClient()
        chains = client.get_chain_rankings()
        assert len(chains) == 3
        assert chains[0].name == "Ethereum"
        assert chains[0].tvl > chains[1].tvl

    @patch("urllib.request.urlopen")
    def test_get_stablecoin_market(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_STABLECOINS)
        client = DefiLlamaClient()
        stables = client.get_stablecoin_market()
        assert len(stables) == 3
        assert stables[0].symbol == "USDT"
        assert stables[0].circulating == 80_000_000_000

    @patch("urllib.request.urlopen")
    def test_protocol_tvl_returns_dict(self, mock_url):
        detail = json.dumps({"name": "Aave", "tvl": [{"date": 1700000000, "totalLiquidityUSD": 10e9}]}).encode()
        mock_url.return_value = _mock_urlopen(detail)
        client = DefiLlamaClient()
        result = client.get_protocol_tvl("aave-v3")
        assert isinstance(result, dict)
        assert result["name"] == "Aave"

    @patch("urllib.request.urlopen")
    def test_empty_protocols(self, mock_url):
        mock_url.return_value = _mock_urlopen(b"[]")
        client = DefiLlamaClient()
        assert client.get_top_protocols() == []

    @patch("urllib.request.urlopen")
    def test_empty_yields(self, mock_url):
        mock_url.return_value = _mock_urlopen(json.dumps({"data": []}).encode())
        client = DefiLlamaClient()
        assert client.get_best_yields() == []


class TestYieldTrackerLive:
    """Test live integration on YieldTracker."""

    @patch("urllib.request.urlopen")
    def test_get_live_yields(self, mock_url):
        mock_url.return_value = _mock_urlopen(SAMPLE_YIELDS)
        from defi.yield_tracker import YieldTracker
        tracker = YieldTracker(use_live=True)
        yields = tracker.get_live_yields(min_tvl=100_000)
        assert len(yields) == 3
        assert yields[0]['apy'] >= yields[1]['apy']
        assert 'protocol' in yields[0]
        assert 'chain' in yields[0]

    def test_get_live_yields_fallback(self):
        """On network error, falls back to simulated data."""
        from defi.yield_tracker import YieldTracker
        tracker = YieldTracker(use_live=True)
        # Force failure by giving bad URL
        tracker._llama._timeout = 0.001
        tracker._llama.BASE = "http://localhost:1"
        tracker._llama.YIELDS_BASE = "http://localhost:1"
        result = tracker.get_live_yields()
        # Should fall back to simulated best_yields
        assert len(result) > 0
        assert 'protocol' in result[0]

    def test_simulated_still_works(self):
        """Original simulated API unchanged."""
        from defi.yield_tracker import YieldTracker
        tracker = YieldTracker(use_live=False)
        rates = tracker.get_rates()
        assert 'aave' in rates
        yields = tracker.best_yields()
        assert len(yields) > 0
