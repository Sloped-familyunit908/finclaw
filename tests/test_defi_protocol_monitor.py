"""
Tests for DeFi & Crypto Extensions v4.6.0
Protocol Monitor, On-chain Analyzer, Funding Rate Arbitrage, and Crypto Sentiment.
40+ tests covering all four new modules.
"""

import pytest
from src.defi.protocol_monitor import ProtocolMonitor, Liquidation
from src.defi.onchain import OnChainAnalyzer, MempoolTransaction
from src.defi.funding_arb import FundingRateArbitrage, FundingOpportunity
from src.defi.sentiment import CryptoSentiment


# ============================================================
# ProtocolMonitor Tests (10 tests)
# ============================================================

class TestProtocolMonitor:
    def setup_method(self):
        self.pm = ProtocolMonitor()

    def test_get_tvl_known_protocol(self):
        result = self.pm.get_tvl('aave')
        assert result['protocol'] == 'aave'
        assert result['tvl'] > 0
        assert 'change_1d' in result
        assert 'change_7d' in result
        assert 'chain_tvls' in result

    def test_get_tvl_case_insensitive(self):
        r1 = self.pm.get_tvl('AAVE')
        r2 = self.pm.get_tvl('aave')
        assert r1['tvl'] == r2['tvl']

    def test_get_tvl_unknown_raises(self):
        with pytest.raises(KeyError):
            self.pm.get_tvl('nonexistent_protocol')

    def test_get_yields(self):
        yields = self.pm.get_yields('curve')
        assert len(yields) > 0
        for y in yields:
            assert 'pool' in y
            assert 'apy' in y
            assert y['apy'] > 0
            assert y['protocol'] == 'curve'

    def test_get_yields_unknown_raises(self):
        with pytest.raises(KeyError):
            self.pm.get_yields('nonexistent')

    def test_get_pool_info(self):
        pool = self.pm.get_pool_info('uniswap', 'ETH/USDC')
        assert pool['dex'] == 'uniswap'
        assert pool['pair'] == 'ETH/USDC'
        assert pool['tvl'] > 0
        assert pool['volume_24h'] > 0
        assert pool['apy'] > 0
        assert pool['fee_tier'] == 0.003

    def test_get_pool_info_deterministic(self):
        p1 = self.pm.get_pool_info('uniswap', 'ETH/USDC')
        p2 = self.pm.get_pool_info('uniswap', 'ETH/USDC')
        assert p1 == p2

    def test_monitor_liquidations(self):
        liqs = self.pm.monitor_liquidations('aave')
        assert len(liqs) > 0
        for liq in liqs:
            assert isinstance(liq, Liquidation)
            assert liq.protocol == 'aave'
            assert liq.amount_usd >= 5000

    def test_list_protocols(self):
        protos = self.pm.list_protocols()
        assert 'aave' in protos
        assert 'lido' in protos
        assert protos == sorted(protos)

    def test_top_protocols(self):
        top = self.pm.top_protocols(3)
        assert len(top) == 3
        assert top[0]['tvl'] >= top[1]['tvl'] >= top[2]['tvl']


# ============================================================
# OnChainAnalyzer Tests (10 tests)
# ============================================================

class TestOnChainAnalyzer:
    def setup_method(self):
        self.oc = OnChainAnalyzer()

    def test_whale_tracker_returns_results(self):
        whales = self.oc.whale_tracker('BTC')
        assert len(whales) > 0
        for w in whales:
            assert w['token'] == 'BTC'
            assert w['amount_usd'] >= 100_000

    def test_whale_tracker_min_amount_filter(self):
        whales = self.oc.whale_tracker('ETH', min_amount=1_000_000)
        for w in whales:
            assert w['amount_usd'] >= 1_000_000

    def test_whale_tracker_has_required_fields(self):
        whales = self.oc.whale_tracker('SOL')
        if whales:
            w = whales[0]
            assert 'tx_hash' in w
            assert 'direction' in w
            assert 'from_label' in w
            assert 'to_label' in w

    def test_token_flows_default_exchanges(self):
        flows = self.oc.token_flows('BTC')
        assert flows['token'] == 'BTC'
        assert 'binance' in flows['exchanges']
        assert flows['signal'] in ('bullish', 'bearish')
        assert 'total_inflow' in flows
        assert 'total_outflow' in flows

    def test_token_flows_custom_exchanges(self):
        flows = self.oc.token_flows('ETH', exchanges=['binance', 'coinbase'])
        assert len(flows['exchanges']) == 2
        assert 'binance' in flows['exchanges']
        assert 'coinbase' in flows['exchanges']

    def test_token_flows_net_calculation(self):
        flows = self.oc.token_flows('BTC')
        expected_net = round(flows['total_inflow'] - flows['total_outflow'], 2)
        assert flows['total_net'] == expected_net

    def test_gas_tracker_ethereum(self):
        gas = self.oc.gas_tracker('ethereum')
        assert gas['chain'] == 'ethereum'
        assert gas['slow'] < gas['standard'] < gas['fast'] < gas['rapid']
        assert gas['unit'] == 'gwei'

    def test_gas_tracker_multiple_chains(self):
        for chain in ['ethereum', 'polygon', 'arbitrum', 'bsc']:
            gas = self.oc.gas_tracker(chain)
            assert gas['chain'] == chain
            assert gas['standard'] > 0

    def test_mempool_monitor(self):
        txs = self.oc.mempool_monitor()
        assert len(txs) == 20
        for tx in txs:
            assert isinstance(tx, MempoolTransaction)
            assert tx.tx_type in ('swap', 'transfer', 'contract_call', 'nft_mint')

    def test_mempool_deterministic(self):
        t1 = self.oc.mempool_monitor()
        t2 = self.oc.mempool_monitor()
        assert t1[0].tx_hash == t2[0].tx_hash


# ============================================================
# FundingRateArbitrage Tests (12 tests)
# ============================================================

class TestFundingRateArbitrage:
    def setup_method(self):
        self.fra = FundingRateArbitrage()

    def test_get_funding_rates_default(self):
        rates = self.fra.get_funding_rates()
        assert len(rates) >= 3
        for ex, ex_rates in rates.items():
            assert len(ex_rates) > 0
            for sym, rate in ex_rates.items():
                assert -0.01 < rate < 0.01  # reasonable range

    def test_get_funding_rates_custom_exchanges(self):
        rates = self.fra.get_funding_rates(['binance', 'bybit'])
        assert len(rates) == 2
        assert 'binance' in rates
        assert 'bybit' in rates

    def test_find_opportunities_returns_list(self):
        opps = self.fra.find_opportunities()
        assert isinstance(opps, list)
        for opp in opps:
            assert isinstance(opp, FundingOpportunity)

    def test_find_opportunities_sorted_by_return(self):
        opps = self.fra.find_opportunities(min_spread=0.0)
        if len(opps) > 1:
            for i in range(len(opps) - 1):
                assert opps[i].annualized_return >= opps[i + 1].annualized_return

    def test_find_opportunities_min_spread_filter(self):
        all_opps = self.fra.find_opportunities(min_spread=0.0)
        filtered = self.fra.find_opportunities(min_spread=0.5)
        assert len(filtered) <= len(all_opps)
        for opp in filtered:
            assert opp.annualized_return >= 0.5

    def test_find_opportunities_spread_positive(self):
        opps = self.fra.find_opportunities(min_spread=0.0)
        for opp in opps:
            assert opp.spread >= 0

    def test_calculate_carry(self):
        result = self.fra.calculate_carry('BTC/USDT', period_days=30)
        assert result['symbol'] == 'BTC/USDT'
        assert result['period_days'] == 30
        assert 'avg_funding_rate' in result
        assert 'expected_return' in result
        assert result['direction'] in ('long', 'short')

    def test_calculate_carry_different_periods(self):
        r30 = self.fra.calculate_carry('ETH/USDT', 30)
        r90 = self.fra.calculate_carry('ETH/USDT', 90)
        # Longer period should have proportionally larger expected return
        assert abs(r90['expected_return']) > abs(r30['expected_return']) or r30['avg_funding_rate'] == 0

    def test_calculate_carry_unknown_raises(self):
        with pytest.raises(KeyError):
            self.fra.calculate_carry('NONEXIST/USDT')

    def test_backtest_carry_trade(self):
        result = self.fra.backtest_carry_trade('BTC/USDT')
        assert result['symbol'] == 'BTC/USDT'
        assert result['num_periods'] == 270  # 90 days * 3
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert 'win_rate' in result
        assert 0 <= result['win_rate'] <= 1

    def test_backtest_with_custom_history(self):
        history = [0.0001, -0.0002, 0.0003, 0.0001, -0.0001]
        result = self.fra.backtest_carry_trade('ETH/USDT', history=history)
        assert result['num_periods'] == 5

    def test_backtest_empty_history(self):
        result = self.fra.backtest_carry_trade('BTC/USDT', history=[])
        assert 'error' in result


# ============================================================
# CryptoSentiment Tests (11 tests)
# ============================================================

class TestCryptoSentiment:
    def setup_method(self):
        self.cs = CryptoSentiment()

    def test_fear_greed_index(self):
        fgi = self.cs.fear_greed_index()
        assert 0 <= fgi['value'] <= 100
        assert fgi['classification'] in ('Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed')
        assert fgi['trend'] in ('improving', 'declining', 'stable')

    def test_fear_greed_classification_mapping(self):
        fgi = self.cs.fear_greed_index()
        v = fgi['value']
        c = fgi['classification']
        if v <= 20: assert c == 'Extreme Fear'
        elif v <= 40: assert c == 'Fear'
        elif v <= 60: assert c == 'Neutral'
        elif v <= 80: assert c == 'Greed'
        else: assert c == 'Extreme Greed'

    def test_fear_greed_deterministic(self):
        f1 = self.cs.fear_greed_index()
        f2 = self.cs.fear_greed_index()
        assert f1['value'] == f2['value']

    def test_social_volume(self):
        sv = self.cs.social_volume('BTC')
        assert sv['token'] == 'BTC'
        assert sv['mentions_24h'] > 0
        assert sv['mentions_7d'] > sv['mentions_24h']
        assert sv['dominant_sentiment'] in ('bullish', 'bearish', 'neutral')
        assert -1 <= sv['sentiment_score'] <= 1

    def test_social_volume_different_tokens(self):
        btc = self.cs.social_volume('BTC')
        doge = self.cs.social_volume('DOGE')
        # BTC should generally have more mentions (higher base)
        assert btc['mentions_24h'] != doge['mentions_24h']

    def test_social_volume_case_insensitive(self):
        r1 = self.cs.social_volume('eth')
        r2 = self.cs.social_volume('ETH')
        assert r1['mentions_24h'] == r2['mentions_24h']

    def test_funding_sentiment(self):
        result = self.cs.funding_sentiment('BTC/USDT')
        assert result in ('bullish', 'bearish', 'neutral')

    def test_funding_sentiment_case_insensitive(self):
        r1 = self.cs.funding_sentiment('btc/usdt')
        r2 = self.cs.funding_sentiment('BTC/USDT')
        assert r1 == r2

    def test_funding_sentiment_various_symbols(self):
        for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
            result = self.cs.funding_sentiment(sym)
            assert result in ('bullish', 'bearish', 'neutral')

    def test_composite_sentiment(self):
        result = self.cs.composite_sentiment('BTC')
        assert 'composite_score' in result
        assert result['recommendation'] in ('bullish', 'bearish', 'neutral')
        assert 'components' in result
        assert 'fear_greed' in result['components']
        assert 'social_sentiment' in result['components']
        assert 'funding_sentiment' in result['components']

    def test_composite_sentiment_score_range(self):
        result = self.cs.composite_sentiment('ETH')
        assert -1.5 <= result['composite_score'] <= 1.5
