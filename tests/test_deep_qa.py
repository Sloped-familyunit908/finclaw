"""
FinClaw — Deep QA Test Suite (pytest conversion)
=================================================
Systematic testing of EVERY feature, edge case, and user scenario.
Run with: pytest tests/test_deep_qa.py -m integration
"""
import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.backtester_v7 import BacktesterV7
from agents.stock_picker import MultiFactorPicker
from agents.llm_analyzer import LLMStockAnalyzer, DISRUPTION_DB


pytestmark = pytest.mark.integration
yf = pytest.importorskip("yfinance", reason="yfinance not installed")


def _fetch(ticker: str, period: str = "1y"):
    """Fetch price history via yfinance."""
    import logging
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    try:
        df = yf.Ticker(ticker).history(period=period)
        if df.empty or len(df) < 30:
            return None
        return [
            {"date": idx.to_pydatetime(), "price": float(row["Close"]),
             "volume": float(row["Volume"])}
            for idx, row in df.iterrows()
        ]
    except Exception:
        return None


# ═══ 1. DATA FETCH TESTS ═══

_FETCH_TICKERS = {
    "US large (NVDA)": "NVDA",
    "US mid (CRWD)": "CRWD",
    "A-share Shanghai (600519.SS)": "600519.SS",
    "A-share Shenzhen (002594.SZ)": "002594.SZ",
    "A-share STAR (688256.SS)": "688256.SS",
    "Hong Kong (0700.HK)": "0700.HK",
}


@pytest.mark.parametrize("desc,ticker", list(_FETCH_TICKERS.items()),
                         ids=list(_FETCH_TICKERS.keys()))
def test_data_fetch(desc, ticker):
    h = _fetch(ticker, "1y")
    assert h is not None, f"Failed to fetch {ticker}"
    assert len(h) > 50, f"{ticker} returned only {len(h)} bars"


# ═══ 2. BACKTESTER ROBUSTNESS ═══

@pytest.mark.parametrize("ticker", ["NVDA", "600519.SS", "0700.HK"])
def test_backtester_robustness(ticker):
    h = _fetch(ticker, "1y")
    if h is None:
        pytest.skip(f"No data for {ticker}")

    bt = BacktesterV7(initial_capital=100000)
    r = asyncio.run(bt.run(ticker, "v7", h))

    assert r.total_trades >= 0, "Negative trade count"
    assert -1.0 <= r.max_drawdown <= 0, f"Invalid DD={r.max_drawdown}"
    assert len(r.equity_curve) > 0, "Empty equity curve"
    assert min(r.equity_curve) >= 0, f"Equity went negative: {min(r.equity_curve)}"
    assert 0 <= r.win_rate <= 1, f"Invalid win rate: {r.win_rate}"


# ═══ 3. PICKER ON REAL DATA ═══

@pytest.mark.parametrize("ticker", ["NVDA", "INTC"])
def test_picker_real_data(ticker):
    h = _fetch(ticker, "1y")
    if h is None:
        pytest.skip(f"No data for {ticker}")

    picker = MultiFactorPicker(use_fundamentals=True)
    a = picker.analyze(ticker, h, ticker)

    assert a.score is not None
    assert a.conviction is not None
    assert len(a.factors) >= 5, f"Only {len(a.factors)} factors"


# ═══ 4. LLM ANALYZER ═══

@pytest.mark.parametrize("ticker", list(DISRUPTION_DB.keys())[:10])
def test_llm_disruption_score(ticker):
    llm = LLMStockAnalyzer()
    adj, reason = llm.compute_ai_era_score(ticker, 0.5)
    assert -0.5 <= adj <= 1.5, f"Score out of range: {adj}"


# ═══ 5. DIFFERENT CAPITAL SIZES ═══

@pytest.mark.parametrize("capital", [1000, 10000, 100000, 1000000, 10000000])
def test_capital_sizes(capital):
    h = _fetch("AAPL", "1y")
    if h is None:
        pytest.skip("No data for AAPL")

    bt = BacktesterV7(initial_capital=capital)
    r = asyncio.run(bt.run("AAPL", "v7", h))
    final = capital * (1 + r.total_return)
    assert final > 0, f"Final capital went to zero/negative: {final}"


# ═══ 6. DIFFERENT TIME PERIODS ═══

@pytest.mark.parametrize("period", ["3mo", "6mo", "1y", "2y", "5y"])
def test_time_periods(period):
    h = _fetch("MSFT", period)
    if h is None or len(h) < 60:
        pytest.skip(f"Insufficient data for MSFT {period}")

    bt = BacktesterV7(initial_capital=10000)
    r = asyncio.run(bt.run("MSFT", "v7", h))
    assert isinstance(r.total_return, (int, float))


# ═══ 7. CONCURRENT BACKTESTS ═══

def test_concurrent_backtests():
    tickers = ["AAPL", "MSFT", "GOOG"]
    histories = {}
    for t in tickers:
        h = _fetch(t, "1y")
        if h:
            histories[t] = h
    if not histories:
        pytest.skip("No data for any ticker")

    async def _run_all():
        tasks = []
        for t, h in histories.items():
            bt = BacktesterV7(initial_capital=10000)
            tasks.append(bt.run(t, "v7", h))
        return await asyncio.gather(*tasks)

    results = asyncio.run(_run_all())
    assert len(results) == len(histories)
    for r in results:
        assert isinstance(r.total_return, (int, float))


# ═══ 8. OUTPUT FORMAT ═══

def test_output_format():
    h = _fetch("META", "1y")
    if h is None:
        pytest.skip("No data for META")

    bt = BacktesterV7(initial_capital=10000)
    r = asyncio.run(bt.run("META", "v7", h))

    for field in ["total_return", "total_trades", "win_rate", "max_drawdown",
                  "sharpe_ratio", "equity_curve", "trades"]:
        assert hasattr(r, field), f"BacktestResult missing '{field}'"

    if r.trades:
        t = r.trades[0]
        for field in ["entry_price", "exit_price", "entry_time", "exit_time",
                       "pnl", "pnl_pct", "signal_source"]:
            assert hasattr(t, field), f"Trade missing '{field}'"
