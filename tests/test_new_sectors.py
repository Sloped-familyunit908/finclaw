"""
FinClaw — New Sectors Test (pytest conversion)
================================================
Tests new sector tickers, universe sizes, cross-market linkages, and backtesting.
Run with: pytest tests/test_new_sectors.py -m integration
"""
import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.backtester_v7 import BacktesterV7
from agents.universe import (
    A_SHARES_EXTENDED, US_EXTENDED, HK_EXTENDED,
    SECTOR_LINKAGE, get_linked_stocks,
)

pytestmark = pytest.mark.integration
yf = pytest.importorskip("yfinance", reason="yfinance not installed")


def _fetch(ticker: str):
    """Fetch 1y price history via yfinance."""
    import logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    try:
        df = yf.Ticker(ticker).history(period="1y")
        if df.empty or len(df) < 60:
            return None
        return [
            {"date": idx.to_pydatetime(), "price": float(row["Close"]),
             "volume": float(row["Volume"])}
            for idx, row in df.iterrows()
        ]
    except Exception:
        return None


# ═══ Universe Size Tests ═══

@pytest.mark.parametrize("name,universe", [
    ("US", US_EXTENDED), ("CN", A_SHARES_EXTENDED), ("HK", HK_EXTENDED),
])
def test_universe_size(name, universe):
    assert len(universe) >= 20, f"{name} universe only has {len(universe)} stocks"


# ═══ New A-share Sector Tickers ═══

_NEW_TICKERS = {
    "optical_module/002281.SZ": "002281.SZ",
    "optical_module/300308.SZ": "300308.SZ",
    "pcb/002938.SZ": "002938.SZ",
    "pcb/002916.SZ": "002916.SZ",
    "ai_apps/688047.SS": "688047.SS",
    "ai_apps/002410.SZ": "002410.SZ",
    "space/688066.SS": "688066.SS",
    "space/600118.SS": "600118.SS",
}


@pytest.mark.parametrize("desc,ticker", list(_NEW_TICKERS.items()),
                         ids=list(_NEW_TICKERS.keys()))
def test_new_ticker_in_universe(desc, ticker):
    assert ticker in A_SHARES_EXTENDED, f"{ticker} not in A_SHARES_EXTENDED"


# ═══ Sector Linkage Tests ═══

@pytest.mark.parametrize("sector", [
    "optical_module", "pcb_electronics", "commercial_space", "ai_applications",
])
def test_sector_linkage_exists(sector):
    assert sector in SECTOR_LINKAGE, f"Sector {sector} not in SECTOR_LINKAGE"
    link = SECTOR_LINKAGE[sector]
    assert "correlation" in link, f"Missing correlation for {sector}"


def test_cross_market_linkage_nvda():
    linked = get_linked_stocks("NVDA")
    assert linked, "NVDA should have linked stocks"
    total_linked = sum(len(l["linked_tickers"]) for l in linked)
    assert total_linked > 0, "NVDA should have at least one linked ticker"


def test_cross_market_linkage_guangxun():
    linked = get_linked_stocks("002281.SZ")
    assert linked, "002281.SZ should have linked stocks"
    assert linked[0]["sector"], "Linkage should have a sector"


# ═══ Backtest on New Sector Stocks ═══

_BACKTEST_TICKERS = {
    "Zhongji Innolight (Optical)": "300308.SZ",
    "Shennan Circuits (PCB)": "002938.SZ",
    "Guangxun Tech (Optical)": "002281.SZ",
}


@pytest.mark.parametrize("name,ticker", list(_BACKTEST_TICKERS.items()),
                         ids=list(_BACKTEST_TICKERS.keys()))
def test_backtest_new_sector(name, ticker):
    h = _fetch(ticker)
    if h is None:
        pytest.skip(f"No data for {ticker}")

    bt = BacktesterV7(initial_capital=100000)
    r = asyncio.run(bt.run(ticker, "v7", h))
    assert isinstance(r.total_return, (int, float))
    assert 0 <= r.win_rate <= 1


# ═══ Existing Stocks Still Work ═══

@pytest.mark.parametrize("ticker", ["NVDA", "600519.SS", "0700.HK"])
def test_existing_stocks_not_broken(ticker):
    h = _fetch(ticker)
    if h is None:
        pytest.skip(f"No data for {ticker}")

    bt = BacktesterV7(initial_capital=100000)
    r = asyncio.run(bt.run(ticker, "v7", h))
    assert -1.0 <= r.total_return <= 10.0, f"Invalid return: {r.total_return}"
    assert 0 <= r.win_rate <= 1, f"Invalid win rate: {r.win_rate}"
