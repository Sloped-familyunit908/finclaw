"""Tests for SectorRotation strategy."""

import pytest
from src.strategies.sector_rotation import SectorRotation, SectorSignal


def _make_sector_data(n=100, trend=0.001):
    """Generate fake price data for all sectors."""
    import random
    random.seed(42)
    data = {}
    for symbol in SectorRotation.SECTORS:
        prices = [100.0]
        for i in range(n):
            # Different trend per sector
            offset = hash(symbol) % 10 * 0.0005
            prices.append(prices[-1] * (1 + trend + offset + random.gauss(0, 0.01)))
        data[symbol] = prices
    return data


class TestSectorRotation:
    def test_rank_sectors_basic(self):
        data = _make_sector_data()
        sr = SectorRotation()
        ranked = sr.rank_sectors(data)
        assert len(ranked) == 11
        assert ranked[0].rank == 1
        assert ranked[-1].rank == 11
        assert all(isinstance(s, SectorSignal) for s in ranked)

    def test_rank_sectors_sorted_by_score(self):
        data = _make_sector_data()
        sr = SectorRotation()
        ranked = sr.rank_sectors(data)
        scores = [s.score for s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_sectors_actions(self):
        data = _make_sector_data()
        sr = SectorRotation()
        ranked = sr.rank_sectors(data)
        buy = [s for s in ranked if s.action == 'buy']
        hold = [s for s in ranked if s.action == 'hold']
        sell = [s for s in ranked if s.action == 'sell']
        assert len(buy) == 3
        assert len(hold) == 3
        assert len(sell) == 5

    def test_rank_sectors_custom_lookback(self):
        data = _make_sector_data(n=200)
        sr = SectorRotation()
        r1 = sr.rank_sectors(data, lookback=20)
        r2 = sr.rank_sectors(data, lookback=100)
        assert len(r1) == 11
        assert len(r2) == 11

    def test_rank_sectors_insufficient_data(self):
        data = {'XLK': [100, 101], 'XLF': [100]}
        sr = SectorRotation()
        ranked = sr.rank_sectors(data, lookback=63)
        assert len(ranked) == 0

    def test_rank_sectors_invalid_lookback(self):
        sr = SectorRotation()
        with pytest.raises(ValueError):
            sr.rank_sectors({}, lookback=0)

    def test_generate_signals(self):
        data = _make_sector_data()
        sr = SectorRotation()
        signals = sr.generate_signals(data, top_n=3)
        buys = [s for s in signals if s.action == 'buy']
        sells = [s for s in signals if s.action == 'sell']
        assert len(buys) == 3
        assert len(sells) == 8

    def test_generate_signals_top_5(self):
        data = _make_sector_data()
        sr = SectorRotation()
        signals = sr.generate_signals(data, top_n=5)
        buys = [s for s in signals if s.action == 'buy']
        assert len(buys) == 5

    def test_regime_adjusted_bull(self):
        data = _make_sector_data()
        sr = SectorRotation()
        adjusted = sr.regime_adjusted(data, 'bull')
        assert len(adjusted) == 11
        assert adjusted[0].rank == 1

    def test_regime_adjusted_bear(self):
        data = _make_sector_data()
        sr = SectorRotation()
        adjusted = sr.regime_adjusted(data, 'bear')
        assert len(adjusted) == 11

    def test_regime_adjusted_invalid(self):
        sr = SectorRotation()
        with pytest.raises(ValueError):
            sr.regime_adjusted({}, 'apocalypse')

    def test_custom_sectors(self):
        sr = SectorRotation(sectors={'XLK': 'Tech', 'XLF': 'Fin'})
        data = {'XLK': list(range(100, 200)), 'XLF': list(range(100, 200))}
        ranked = sr.rank_sectors(data, lookback=10)
        assert len(ranked) == 2
