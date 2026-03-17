"""Tests for FinClaw v2.8.0 — Crypto & DeFi features."""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from strategies.crypto_strategies import GridBot, DCAStrategy, ArbitrageDetector, GridSignal, DCASignal, ArbitrageOpportunity
from defi.yield_tracker import YieldTracker, YieldInfo
from crypto.onchain import OnChainAnalytics, WhaleTransaction
from crypto.rebalancer import CryptoRebalancer, RebalanceTrade
from ml.regime_detector import RegimeDetector, RegimeState


# ─── GridBot Tests ───────────────────────────────────────────────────

class TestGridBot:
    def test_init_basic(self):
        bot = GridBot(lower=100, upper=200, grids=5)
        assert bot.lower == 100
        assert bot.upper == 200
        assert bot.grids == 5

    def test_grid_levels_count(self):
        bot = GridBot(lower=100, upper=200, grids=5)
        assert len(bot.grid_levels) == 6  # grids + 1

    def test_grid_levels_range(self):
        bot = GridBot(lower=100, upper=200, grids=4)
        assert bot.grid_levels[0] == 100
        assert bot.grid_levels[-1] == 200

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            GridBot(lower=200, upper=100)

    def test_invalid_grids(self):
        with pytest.raises(ValueError):
            GridBot(lower=100, upper=200, grids=1)

    def test_generate_signals_buy(self):
        bot = GridBot(lower=90, upper=110, grids=2)
        # levels: 90, 100, 110
        data = [{'close': 105}, {'close': 95}]  # crosses down through 100
        signals = bot.generate_signals(data)
        assert len(signals) == 2
        assert signals[1].action == 'buy'

    def test_generate_signals_sell(self):
        bot = GridBot(lower=90, upper=110, grids=2)
        data = [{'close': 95}, {'close': 105}]  # crosses up through 100
        signals = bot.generate_signals(data)
        assert signals[1].action == 'sell'

    def test_generate_signals_hold(self):
        bot = GridBot(lower=90, upper=110, grids=2)
        data = [{'close': 95}, {'close': 96}]  # no grid crossed
        signals = bot.generate_signals(data)
        assert signals[1].action == 'hold'

    def test_summary(self):
        bot = GridBot(lower=100, upper=200, grids=10)
        s = bot.summary()
        assert s['grids'] == 10
        assert s['grid_spacing'] == 10.0
        assert len(s['levels']) == 11


# ─── DCAStrategy Tests ──────────────────────────────────────────────

class TestDCAStrategy:
    def test_init_valid(self):
        dca = DCAStrategy(amount_per_period=100, period='weekly')
        assert dca.amount_per_period == 100
        assert dca.period == 'weekly'

    def test_invalid_amount(self):
        with pytest.raises(ValueError):
            DCAStrategy(amount_per_period=-10)

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            DCAStrategy(amount_per_period=100, period='yearly')

    def test_generate_signals_daily(self):
        dca = DCAStrategy(amount_per_period=50, period='daily')
        data = [{'close': 100 + i} for i in range(5)]
        signals = dca.generate_signals(data)
        assert all(s.action == 'buy' for s in signals)

    def test_generate_signals_weekly(self):
        dca = DCAStrategy(amount_per_period=100, period='weekly')
        data = [{'close': 50000 + i * 100} for i in range(14)]
        signals = dca.generate_signals(data)
        buy_count = sum(1 for s in signals if s.action == 'buy')
        assert buy_count == 2  # day 0 and day 7

    def test_backtest(self):
        dca = DCAStrategy(amount_per_period=100, period='daily')
        data = [{'close': 100}] * 10
        result = dca.backtest(data)
        assert result['num_buys'] == 10
        assert result['total_invested'] == 1000
        assert result['avg_price'] == 100


# ─── ArbitrageDetector Tests ────────────────────────────────────────

class TestArbitrageDetector:
    def test_detect_opportunity(self):
        detector = ArbitrageDetector(min_spread_pct=0.5, fee_pct=0.1)
        prices = {'BTC': {'binance': 60000, 'coinbase': 61000}}
        opps = detector.detect(prices)
        assert len(opps) > 0
        assert opps[0].buy_exchange == 'binance'
        assert opps[0].sell_exchange == 'coinbase'

    def test_no_opportunity(self):
        detector = ArbitrageDetector(min_spread_pct=5.0, fee_pct=0.1)
        prices = {'BTC': {'binance': 60000, 'coinbase': 60100}}
        opps = detector.detect(prices)
        assert len(opps) == 0

    def test_multiple_tokens(self):
        detector = ArbitrageDetector(min_spread_pct=0.1, fee_pct=0.05)
        prices = {
            'BTC': {'binance': 60000, 'kraken': 60500},
            'ETH': {'binance': 3000, 'coinbase': 3050},
        }
        opps = detector.detect(prices)
        assert len(opps) >= 2

    def test_best_opportunity(self):
        detector = ArbitrageDetector(min_spread_pct=0.1, fee_pct=0.05)
        prices = {'BTC': {'a': 100, 'b': 102}}
        best = detector.best_opportunity(prices)
        assert best is not None
        assert best.spread_pct > 0


# ─── YieldTracker Tests ─────────────────────────────────────────────

class TestYieldTracker:
    def test_get_all_rates(self):
        tracker = YieldTracker()
        rates = tracker.get_rates()
        assert len(rates) > 0
        assert 'aave' in rates

    def test_get_specific_protocols(self):
        tracker = YieldTracker()
        rates = tracker.get_rates(['aave', 'lido'])
        assert len(rates) == 2

    def test_get_unknown_protocol(self):
        tracker = YieldTracker()
        rates = tracker.get_rates(['nonexistent'])
        assert len(rates) == 0

    def test_best_yields(self):
        tracker = YieldTracker()
        yields = tracker.best_yields(min_tvl=1e6)
        assert len(yields) > 0
        # Should be sorted by APY descending
        for i in range(len(yields) - 1):
            assert yields[i]['apy'] >= yields[i + 1]['apy']

    def test_best_yields_high_tvl_filter(self):
        tracker = YieldTracker()
        yields = tracker.best_yields(min_tvl=10_000_000_000)
        # Only lido stETH has TVL >= 10B
        assert all(y['tvl'] >= 10_000_000_000 for y in yields)

    def test_compare_protocols(self):
        tracker = YieldTracker()
        comparison = tracker.compare_protocols()
        assert 'aave' in comparison
        assert 'avg_apy' in comparison['aave']
        assert 'total_tvl' in comparison['aave']

    def test_risk_score(self):
        tracker = YieldTracker()
        score = tracker.risk_score('aave')
        assert 0 <= score <= 1

    def test_risk_score_unknown(self):
        tracker = YieldTracker()
        with pytest.raises(KeyError):
            tracker.risk_score('nonexistent')


# ─── OnChainAnalytics Tests ─────────────────────────────────────────

class TestOnChainAnalytics:
    def test_whale_transactions(self):
        analytics = OnChainAnalytics()
        txs = analytics.whale_transactions('BTC')
        assert len(txs) > 0
        assert all(isinstance(t, WhaleTransaction) for t in txs)
        assert all(t.amount_usd >= 100000 for t in txs)

    def test_whale_high_min(self):
        analytics = OnChainAnalytics()
        txs = analytics.whale_transactions('BTC', min_usd=1_500_000)
        assert all(t.amount_usd >= 1_500_000 for t in txs)

    def test_exchange_flows(self):
        analytics = OnChainAnalytics()
        flows = analytics.exchange_flows('ETH')
        assert 'inflow' in flows
        assert 'outflow' in flows
        assert 'net' in flows
        assert flows['signal'] in ('bullish', 'bearish')

    def test_active_addresses(self):
        analytics = OnChainAnalytics()
        addrs = analytics.active_addresses('BTC')
        assert addrs['active_24h'] > 0
        assert addrs['active_7d'] > 0
        assert addrs['trend'] in ('increasing', 'decreasing')

    def test_gas_tracker(self):
        analytics = OnChainAnalytics()
        gas = analytics.gas_tracker()
        assert gas['unit'] == 'gwei'
        assert gas['slow'] < gas['standard'] < gas['fast'] < gas['rapid']

    def test_deterministic(self):
        a1 = OnChainAnalytics(seed=42)
        a2 = OnChainAnalytics(seed=42)
        assert a1.exchange_flows('BTC') == a2.exchange_flows('BTC')


# ─── CryptoRebalancer Tests ─────────────────────────────────────────

class TestCryptoRebalancer:
    def test_init_valid(self):
        r = CryptoRebalancer({'BTC': 0.6, 'ETH': 0.4})
        assert r.target_allocation['BTC'] == 0.6

    def test_init_invalid_sum(self):
        with pytest.raises(ValueError):
            CryptoRebalancer({'BTC': 0.5, 'ETH': 0.3})

    def test_init_negative(self):
        with pytest.raises(ValueError):
            CryptoRebalancer({'BTC': 1.5, 'ETH': -0.5})

    def test_calculate_trades(self):
        r = CryptoRebalancer({'BTC': 0.5, 'ETH': 0.5})
        holdings = {'BTC': 1, 'ETH': 0}
        prices = {'BTC': 60000, 'ETH': 3000}
        trades = r.calculate_trades(holdings, prices)
        assert len(trades) > 0
        # Should sell BTC and buy ETH
        btc_trade = next(t for t in trades if t.token == 'BTC')
        eth_trade = next(t for t in trades if t.token == 'ETH')
        assert btc_trade.action == 'sell'
        assert eth_trade.action == 'buy'

    def test_already_balanced(self):
        r = CryptoRebalancer({'BTC': 0.5, 'ETH': 0.5})
        holdings = {'BTC': 1, 'ETH': 20}
        prices = {'BTC': 60000, 'ETH': 3000}
        trades = r.calculate_trades(holdings, prices)
        assert len(trades) == 0

    def test_needs_rebalance(self):
        r = CryptoRebalancer({'BTC': 0.5, 'ETH': 0.5})
        assert r.needs_rebalance({'BTC': 2, 'ETH': 1}, {'BTC': 60000, 'ETH': 3000})

    def test_drift(self):
        r = CryptoRebalancer({'BTC': 0.5, 'ETH': 0.5})
        drift = r.drift({'BTC': 1, 'ETH': 20}, {'BTC': 60000, 'ETH': 3000})
        assert abs(drift['BTC']) < 1  # roughly balanced

    def test_backtest_rebalancing(self):
        r = CryptoRebalancer({'BTC': 0.6, 'ETH': 0.4})
        data = [{'prices': {'BTC': 60000 + i * 100, 'ETH': 3000 + i * 10}} for i in range(60)]
        result = r.backtest_rebalancing(data, period='monthly')
        assert result['start_value'] == 10000
        assert result['end_value'] > 0
        assert result['num_rebalances'] >= 1


# ─── RegimeDetector Tests ───────────────────────────────────────────

class TestRegimeDetector:
    def test_detect_bull(self):
        detector = RegimeDetector(lookback=10)
        returns = [0.05] * 20  # consistent positive
        assert detector.detect(returns) == 'bull'

    def test_detect_bear(self):
        detector = RegimeDetector(lookback=10)
        returns = [-0.05] * 20
        assert detector.detect(returns) == 'bear'

    def test_detect_sideways(self):
        detector = RegimeDetector(lookback=10)
        returns = [0.001, -0.001] * 10  # tiny oscillation
        assert detector.detect(returns) == 'sideways'

    def test_detect_volatile(self):
        detector = RegimeDetector(lookback=10, vol_threshold=0.03)
        returns = [0.1, -0.1] * 10  # high vol
        assert detector.detect(returns) == 'volatile'

    def test_detect_empty(self):
        detector = RegimeDetector()
        assert detector.detect([]) == 'sideways'

    def test_detect_detailed(self):
        detector = RegimeDetector(lookback=10)
        returns = [0.05] * 20
        state = detector.detect_detailed(returns)
        assert isinstance(state, RegimeState)
        assert state.regime == 'bull'
        assert state.confidence > 0

    def test_transition_matrix(self):
        detector = RegimeDetector(lookback=5)
        returns = [0.05] * 20 + [-0.05] * 20
        matrix = detector.transition_matrix(returns)
        assert 'bull' in matrix
        # bull→bull should be high probability
        assert matrix['bull']['bull'] > 0

    def test_regime_history(self):
        detector = RegimeDetector(lookback=5)
        returns = [0.05] * 10
        history = detector.regime_history(returns)
        assert len(history) > 0
        assert all(h['regime'] in RegimeDetector.REGIMES for h in history)

    def test_optimal_strategy_bull(self):
        detector = RegimeDetector()
        assert 'trend_following' in detector.optimal_strategy('bull')

    def test_optimal_strategy_bear(self):
        detector = RegimeDetector()
        assert 'defensive' in detector.optimal_strategy('bear')

    def test_optimal_strategy_sideways(self):
        detector = RegimeDetector()
        assert 'grid_trading' in detector.optimal_strategy('sideways')

    def test_optimal_strategy_unknown(self):
        detector = RegimeDetector()
        assert detector.optimal_strategy('unknown') == 'unknown regime'
