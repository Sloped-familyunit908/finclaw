"""Tests for universe.py — stock universes and sector linkages."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from agents.universe import US_EXTENDED, A_SHARES_EXTENDED, HK_EXTENDED


class TestUniverseData:
    def test_us_has_nvidia(self):
        assert "NVDA" in US_EXTENDED

    def test_china_has_stocks(self):
        assert len(A_SHARES_EXTENDED) > 30

    def test_hk_has_stocks(self):
        assert len(HK_EXTENDED) > 10

    def test_no_duplicate_tickers_us(self):
        tickers = list(US_EXTENDED.keys())
        assert len(tickers) == len(set(tickers))

    def test_sector_linkage_exists(self):
        from agents.universe import SECTOR_LINKAGE
        assert len(SECTOR_LINKAGE) > 0
        for name, link in SECTOR_LINKAGE.items():
            assert "correlation" in link
