"""
Tests for FinClaw v2.7.0 — Real-time Data & Streaming
30+ tests covering all new modules.
"""

import asyncio
import math
import os
import tempfile
import pytest

from src.data.streaming import MarketDataStream, MarketTick
from src.ta.realtime_ta import RealtimeTA, SUPPORTED_INDICATORS
from src.risk.position_sizer import PositionSizer
from src.analytics.correlation import CorrelationAnalyzer
from src.data.economic_calendar import EconomicCalendar, EconomicEvent

from datetime import datetime, timedelta, timezone


# ─── MarketDataStream ────────────────────────────────────────────

class TestMarketDataStream:
    def test_subscribe_and_tickers(self):
        s = MarketDataStream()
        s.subscribe('AAPL', lambda t: None)
        assert 'AAPL' in s.subscribed_tickers

    def test_subscribe_uppercase(self):
        s = MarketDataStream()
        s.subscribe('aapl', lambda t: None)
        assert 'AAPL' in s.subscribed_tickers

    def test_unsubscribe_all(self):
        s = MarketDataStream()
        s.subscribe('AAPL', lambda t: None)
        s.unsubscribe('AAPL')
        assert 'AAPL' not in s.subscribed_tickers

    def test_unsubscribe_specific_callback(self):
        s = MarketDataStream()
        cb1 = lambda t: None
        cb2 = lambda t: None
        s.subscribe('AAPL', cb1)
        s.subscribe('AAPL', cb2)
        s.unsubscribe('AAPL', cb1)
        assert len(s.subscribers['AAPL']) == 1

    def test_inject_tick(self):
        s = MarketDataStream()
        received = []
        s.subscribe('AAPL', lambda t: received.append(t))
        tick = MarketTick(ticker='AAPL', price=150.0, volume=1000)
        asyncio.run(s.inject_tick(tick))
        assert len(received) == 1
        assert received[0].price == 150.0

    def test_tick_count(self):
        s = MarketDataStream()
        s.subscribe('AAPL', lambda t: None)
        asyncio.run(s.inject_tick(MarketTick(ticker='AAPL', price=150.0)))
        asyncio.run(s.inject_tick(MarketTick(ticker='AAPL', price=151.0)))
        assert s.tick_count == 2

    def test_last_tick(self):
        s = MarketDataStream()
        s.subscribe('AAPL', lambda t: None)
        asyncio.run(s.inject_tick(MarketTick(ticker='AAPL', price=155.0)))
        assert s.last_tick('AAPL').price == 155.0

    def test_connect_invalid_source(self):
        s = MarketDataStream()
        with pytest.raises(ValueError):
            asyncio.run(s.connect('invalid_source'))

    def test_connect_valid(self):
        s = MarketDataStream()
        assert asyncio.run(s.connect('mock'))

    def test_stats(self):
        s = MarketDataStream()
        s.subscribe('AAPL', lambda t: None)
        stats = s.stats()
        assert stats['subscriptions'] == 1
        assert 'AAPL' in stats['tickers']

    def test_market_tick_spread(self):
        t = MarketTick(ticker='AAPL', price=150.0, bid=149.99, ask=150.01)
        assert abs(t.spread - 0.02) < 1e-6

    def test_no_duplicate_subscribe(self):
        s = MarketDataStream()
        cb = lambda t: None
        s.subscribe('AAPL', cb)
        s.subscribe('AAPL', cb)
        assert len(s.subscribers['AAPL']) == 1


# ─── RealtimeTA ──────────────────────────────────────────────────

class TestRealtimeTA:
    def test_ema_single_value(self):
        ta = RealtimeTA(['ema'], ema_period=10)
        result = ta.update(100.0)
        assert result['ema'] == 100.0

    def test_ema_converges(self):
        ta = RealtimeTA(['ema'], ema_period=5)
        for _ in range(100):
            result = ta.update(50.0)
        assert abs(result['ema'] - 50.0) < 0.01

    def test_rsi_neutral_start(self):
        ta = RealtimeTA(['rsi'])
        result = ta.update(100.0)
        assert result['rsi'] == 50.0

    def test_rsi_rising_prices(self):
        ta = RealtimeTA(['rsi'], rsi_period=14)
        for i in range(30):
            result = ta.update(100.0 + i)
        assert result['rsi'] > 70

    def test_rsi_falling_prices(self):
        ta = RealtimeTA(['rsi'], rsi_period=14)
        for i in range(30):
            result = ta.update(200.0 - i)
        assert result['rsi'] < 30

    def test_macd_keys(self):
        ta = RealtimeTA(['macd'])
        result = ta.update(100.0)
        assert 'macd_line' in result
        assert 'macd_signal' in result
        assert 'macd_histogram' in result

    def test_vwap_with_volume(self):
        ta = RealtimeTA(['vwap'])
        ta.update(100.0, volume=1000)
        result = ta.update(110.0, volume=1000)
        assert abs(result['vwap'] - 105.0) < 0.01

    def test_bollinger_keys(self):
        ta = RealtimeTA(['bollinger'])
        result = ta.update(100.0)
        assert 'bb_upper' in result
        assert 'bb_middle' in result
        assert 'bb_lower' in result

    def test_unsupported_indicator(self):
        with pytest.raises(ValueError):
            RealtimeTA(['nonexistent'])

    def test_tick_count(self):
        ta = RealtimeTA(['ema'])
        ta.update(100.0)
        ta.update(101.0)
        assert ta.tick_count == 2

    def test_multiple_indicators(self):
        ta = RealtimeTA(['ema', 'rsi', 'macd'])
        result = ta.update(100.0)
        assert 'ema' in result
        assert 'rsi' in result
        assert 'macd_line' in result


# ─── PositionSizer ───────────────────────────────────────────────

class TestPositionSizer:
    def test_fixed_dollar(self):
        assert PositionSizer.fixed_dollar(100000, 2000) == pytest.approx(0.02)

    def test_fixed_dollar_zero_capital(self):
        assert PositionSizer.fixed_dollar(0, 1000) == 0.0

    def test_fixed_dollar_capped(self):
        assert PositionSizer.fixed_dollar(1000, 2000) == 1.0

    def test_percent_risk(self):
        shares = PositionSizer.percent_risk(100000, 50.0, 48.0, 0.02)
        assert shares == 1000  # risk $2000, stop $2 away

    def test_percent_risk_zero_stop(self):
        assert PositionSizer.percent_risk(100000, 50.0, 50.0) == 0

    def test_kelly_positive_edge(self):
        f = PositionSizer.kelly(0.6, 1.5, fraction=0.5)
        assert 0 < f < 1

    def test_kelly_no_edge(self):
        assert PositionSizer.kelly(0.3, 0.5) == 0.0

    def test_volatility_based(self):
        shares = PositionSizer.volatility_based(100000, 100.0, 2.0, 0.02)
        assert shares == 1000  # risk $2000, ATR $2

    def test_volatility_based_zero_atr(self):
        assert PositionSizer.volatility_based(100000, 100.0, 0, 0.02) == 0

    def test_optimal_f_basic(self):
        trades = [100, -50, 150, -80, 200, -30, 50, -60]
        f = PositionSizer.optimal_f(trades)
        assert 0 < f <= 1.0

    def test_optimal_f_all_wins(self):
        assert PositionSizer.optimal_f([100, 200, 50]) == 0.0

    def test_equal_weight(self):
        assert PositionSizer.equal_weight(5) == pytest.approx(0.2)

    def test_equal_weight_zero(self):
        assert PositionSizer.equal_weight(0) == 0.0


# ─── CorrelationAnalyzer ─────────────────────────────────────────

class TestCorrelationAnalyzer:
    def _sample_returns(self):
        import random
        random.seed(42)
        n = 100
        a = [random.gauss(0, 0.01) for _ in range(n)]
        b = [x + random.gauss(0, 0.005) for x in a]  # correlated with a
        c = [random.gauss(0, 0.01) for _ in range(n)]  # uncorrelated
        return {'A': a, 'B': b, 'C': c}

    def test_compute(self):
        ca = CorrelationAnalyzer()
        returns = self._sample_returns()
        matrix = ca.compute(returns)
        assert matrix['A']['A'] == pytest.approx(1.0)
        assert abs(matrix['A']['B']) > 0.5  # should be highly correlated

    def test_find_uncorrelated(self):
        ca = CorrelationAnalyzer()
        returns = self._sample_returns()
        pairs = ca.find_uncorrelated(returns, threshold=0.5)
        # A-C and B-C should be uncorrelated
        tickers_in_pairs = set()
        for a, b, _ in pairs:
            tickers_in_pairs.add(a)
            tickers_in_pairs.add(b)
        assert 'C' in tickers_in_pairs

    def test_render_heatmap(self):
        ca = CorrelationAnalyzer()
        returns = self._sample_returns()
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            path = f.name
        try:
            ca.render_heatmap_html(returns, path)
            with open(path) as f:
                html = f.read()
            assert 'Correlation' in html
            assert '<table' in html
        finally:
            os.unlink(path)

    def test_diversification_ratio(self):
        ca = CorrelationAnalyzer()
        returns = self._sample_returns()
        weights = {'A': 0.33, 'B': 0.33, 'C': 0.34}
        dr = ca.diversification_ratio(returns, weights)
        assert dr >= 1.0  # diversification benefit

    def test_correlation_symmetry(self):
        ca = CorrelationAnalyzer()
        returns = self._sample_returns()
        matrix = ca.compute(returns)
        assert matrix['A']['B'] == pytest.approx(matrix['B']['A'])


# ─── EconomicCalendar ────────────────────────────────────────────

class TestEconomicCalendar:
    def test_upcoming_events(self):
        cal = EconomicCalendar()
        events = cal.upcoming_events(days=30)
        assert len(events) > 0

    def test_high_impact_only(self):
        cal = EconomicCalendar()
        events = cal.high_impact_events(days=30)
        for e in events:
            assert e['impact'] == 'high'

    def test_historical_impact_known(self):
        cal = EconomicCalendar()
        impact = cal.historical_impact('Non-Farm Payrolls')
        assert impact['avg_move'] > 0

    def test_historical_impact_unknown(self):
        cal = EconomicCalendar()
        impact = cal.historical_impact('Made Up Event')
        assert impact['avg_move'] == 0.0

    def test_custom_event(self):
        cal = EconomicCalendar()
        evt = EconomicEvent(
            name='Custom Test',
            date=datetime.now(timezone.utc) + timedelta(days=1),
            impact='high',
        )
        cal.add_event(evt)
        events = cal.upcoming_events(days=7)
        names = [e['name'] for e in events]
        assert 'Custom Test' in names

    def test_events_by_category(self):
        cal = EconomicCalendar()
        events = cal.events_by_category('inflation', days=30)
        for e in events:
            assert e['category'] == 'inflation'

    def test_event_surprise(self):
        evt = EconomicEvent(name='Test', date=datetime.now(timezone.utc), actual=3.5, forecast=3.0)
        assert evt.surprise == pytest.approx(0.5)

    def test_event_surprise_none(self):
        evt = EconomicEvent(name='Test', date=datetime.now(timezone.utc))
        assert evt.surprise is None
