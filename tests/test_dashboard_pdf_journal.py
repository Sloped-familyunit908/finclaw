"""Tests for v2.2.0 — Interactive Dashboard, PDF Reports, Trade Journal,
Market Calendar, Watchlist Manager.  35+ tests total.
"""
import sys, os, json, datetime, tempfile, shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.dashboard.interactive import InteractiveDashboard
from src.reports.pdf_report import PDFReportGenerator
from src.journal.trade_journal import TradeJournal, Trade
from src.data.market_calendar import MarketCalendar
from src.watchlist.manager import WatchlistManager


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


# =====================================================================
# Interactive Dashboard
# =====================================================================

class TestInteractiveDashboard:
    def test_create_empty(self, tmp_dir):
        d = InteractiveDashboard("Test")
        out = str(tmp_dir / "empty.html")
        html = d.render(out)
        assert "<html" in html
        assert os.path.exists(out)

    def test_add_metric(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_metric("Total Return", 42.5, change=3.2)
        d.add_metric("Sharpe", 1.85)
        html = d.render(str(tmp_dir / "m.html"))
        assert "Total Return" in html
        assert "42.50" in html
        assert "▲" in html

    def test_add_metric_negative_change(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_metric("Drawdown", -15.3, change=-5.1)
        html = d.render(str(tmp_dir / "mn.html"))
        assert "▼" in html

    def test_line_chart(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_chart("line", {"labels": ["Jan", "Feb", "Mar"], "values": [100, 110, 105]}, "Equity Curve")
        html = d.render(str(tmp_dir / "line.html"))
        assert "<svg" in html
        assert "Equity Curve" in html

    def test_bar_chart(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_chart("bar", {"labels": ["Q1", "Q2", "Q3"], "values": [5.2, -2.1, 8.3]}, "Returns")
        html = d.render(str(tmp_dir / "bar.html"))
        assert "<svg" in html

    def test_candlestick_chart(self, tmp_dir):
        d = InteractiveDashboard()
        candles = [
            {"open": 100, "high": 105, "low": 98, "close": 103},
            {"open": 103, "high": 107, "low": 101, "close": 99},
        ]
        d.add_chart("candlestick", {"candles": candles}, "OHLC")
        html = d.render(str(tmp_dir / "candle.html"))
        assert "OHLC" in html

    def test_heatmap_chart(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_chart("heatmap", {
            "matrix": [[1.0, 0.5], [0.5, 1.0]],
            "row_labels": ["AAPL", "MSFT"],
            "col_labels": ["AAPL", "MSFT"],
        }, "Correlation")
        html = d.render(str(tmp_dir / "heat.html"))
        assert "Correlation" in html

    def test_invalid_chart_type(self):
        d = InteractiveDashboard()
        with pytest.raises(ValueError):
            d.add_chart("pie", {}, "Nope")

    def test_table(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_table(["Ticker", "Return"], [["AAPL", "12%"], ["MSFT", "8%"]], "Holdings")
        html = d.render(str(tmp_dir / "tbl.html"))
        assert "AAPL" in html
        assert "<table" in html

    def test_full_dashboard(self, tmp_dir):
        d = InteractiveDashboard("Full Test")
        d.add_metric("NAV", 1250000, change=5.3)
        d.add_chart("line", {"values": list(range(20))}, "Growth")
        d.add_chart("bar", {"labels": [str(i) for i in range(5)], "values": [1, -2, 3, -1, 4]}, "Monthly")
        d.add_table(["A", "B"], [["1", "2"]], "Data")
        html = d.render(str(tmp_dir / "full.html"))
        assert "Full Test" in html
        assert html.count("<svg") == 2

    def test_empty_data_charts(self, tmp_dir):
        d = InteractiveDashboard()
        d.add_chart("line", {"values": []}, "Empty Line")
        d.add_chart("bar", {"values": []}, "Empty Bar")
        d.add_chart("candlestick", {"candles": []}, "Empty Candle")
        d.add_chart("heatmap", {"matrix": []}, "Empty Heat")
        html = d.render(str(tmp_dir / "empty_charts.html"))
        assert "No data" in html


# =====================================================================
# PDF Report Generator
# =====================================================================

class TestPDFReport:
    def test_basic_report(self, tmp_dir):
        r = PDFReportGenerator("Test Report")
        r.add_text("Intro", "Hello world")
        path = r.generate(str(tmp_dir / "report.html"))
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "Hello world" in content

    def test_key_metrics(self, tmp_dir):
        r = PDFReportGenerator()
        r.add_key_metrics({"Sharpe": 1.5, "MaxDD": -12.3})
        path = r.generate(str(tmp_dir / "metrics.html"))
        content = open(path, encoding="utf-8").read()
        assert "Sharpe" in content

    def test_table_section(self, tmp_dir):
        r = PDFReportGenerator()
        r.add_table("Trades", ["Date", "Ticker"], [["2025-01-01", "AAPL"]])
        path = r.generate(str(tmp_dir / "tbl.html"))
        content = open(path, encoding="utf-8").read()
        assert "AAPL" in content

    def test_pdf_fallback(self, tmp_dir):
        """Without weasyprint, .pdf request falls back to .html."""
        r = PDFReportGenerator()
        r.add_text("Test", "content")
        path = r.generate(str(tmp_dir / "out.pdf"))
        assert path.endswith(".html")
        assert os.path.exists(path)

    def test_multiple_sections(self, tmp_dir):
        r = PDFReportGenerator("Multi")
        r.add_text("A", "aaa")
        r.add_text("B", "bbb")
        r.add_key_metrics({"X": 1})
        path = r.generate(str(tmp_dir / "multi.html"))
        content = open(path, encoding="utf-8").read()
        assert "aaa" in content and "bbb" in content


# =====================================================================
# Trade Journal
# =====================================================================

class TestTradeJournal:
    def test_log_and_retrieve(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j.json"))
        t = Trade("AAPL", "buy", 10, 150.0, "2025-01-15", pnl=200)
        j.log_trade(t, notes="earnings play", tags=["earnings"])
        entries = j.get_trades()
        assert len(entries) == 1
        assert entries[0].trade.ticker == "AAPL"

    def test_filter_by_ticker(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j2.json"))
        j.log_trade(Trade("AAPL", "buy", 10, 150, "2025-01-01", 100))
        j.log_trade(Trade("MSFT", "buy", 5, 400, "2025-01-02", 50))
        assert len(j.get_trades(ticker="AAPL")) == 1

    def test_filter_by_date_range(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j3.json"))
        j.log_trade(Trade("X", "buy", 1, 10, "2025-01-01", 0))
        j.log_trade(Trade("X", "buy", 1, 10, "2025-06-01", 0))
        assert len(j.get_trades(date_range=("2025-01-01", "2025-03-01"))) == 1

    def test_analyze(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j4.json"))
        j.log_trade(Trade("A", "buy", 1, 10, "2025-01-01", 100))
        j.log_trade(Trade("B", "sell", 1, 20, "2025-01-02", -50))
        j.log_trade(Trade("C", "buy", 1, 30, "2025-01-03", 200))
        stats = j.analyze()
        assert stats["total_trades"] == 3
        assert stats["win_rate"] == pytest.approx(2 / 3)
        assert stats["best_trade"] == 200
        assert stats["worst_trade"] == -50

    def test_analyze_empty(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j5.json"))
        assert j.analyze()["total_trades"] == 0

    def test_export_csv(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j6.json"))
        j.log_trade(Trade("AAPL", "buy", 10, 150, "2025-01-01", 100), tags=["tech"])
        csv_str = j.export("csv")
        assert "AAPL" in csv_str
        assert "tech" in csv_str

    def test_export_json(self, tmp_dir):
        j = TradeJournal(str(tmp_dir / "j7.json"))
        j.log_trade(Trade("MSFT", "buy", 5, 400, "2025-01-01", 0))
        data = json.loads(j.export("json"))
        assert len(data) == 1

    def test_persistence(self, tmp_dir):
        path = str(tmp_dir / "jp.json")
        j1 = TradeJournal(path)
        j1.log_trade(Trade("X", "buy", 1, 1, "2025-01-01", 0))
        j2 = TradeJournal(path)
        assert len(j2.get_trades()) == 1


# =====================================================================
# Market Calendar
# =====================================================================

class TestMarketCalendar:
    def test_weekday_is_trading(self):
        cal = MarketCalendar()
        # 2025-03-17 is Monday
        assert cal.is_trading_day(datetime.date(2025, 3, 17)) is True

    def test_weekend_not_trading(self):
        cal = MarketCalendar()
        assert cal.is_trading_day(datetime.date(2025, 3, 15)) is False  # Saturday

    def test_christmas_observed(self):
        cal = MarketCalendar()
        assert cal.is_trading_day(datetime.date(2025, 12, 25)) is False

    def test_new_years(self):
        cal = MarketCalendar()
        assert cal.is_trading_day(datetime.date(2025, 1, 1)) is False

    def test_next_trading_day(self):
        cal = MarketCalendar()
        # Friday -> Monday
        nxt = cal.next_trading_day(datetime.date(2025, 3, 14))
        assert nxt == datetime.date(2025, 3, 17)

    def test_trading_days_between(self):
        cal = MarketCalendar()
        days = cal.trading_days_between(datetime.date(2025, 3, 10), datetime.date(2025, 3, 14))
        assert len(days) == 5  # Mon-Fri

    def test_upcoming_holidays(self):
        cal = MarketCalendar()
        holidays = cal.upcoming_holidays(365, from_date=datetime.date(2025, 1, 1))
        names = [name for _, name in holidays]
        assert "Thanksgiving" in names

    def test_string_dates(self):
        cal = MarketCalendar()
        assert cal.is_trading_day("2025-03-17") is True
        assert cal.next_trading_day("2025-03-14") == datetime.date(2025, 3, 17)

    def test_mlk_day(self):
        cal = MarketCalendar()
        # 2025 MLK = Jan 20 (3rd Monday)
        assert cal.is_trading_day(datetime.date(2025, 1, 20)) is False


# =====================================================================
# Watchlist Manager
# =====================================================================

class TestWatchlistManager:
    def test_create_and_list(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl.json"))
        wm.create("tech", ["AAPL", "MSFT", "GOOG"])
        assert "tech" in wm.list_all()
        wl = wm.get("tech")
        assert "AAPL" in wl.tickers

    def test_add_ticker(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl2.json"))
        wm.create("test", [])
        wm.add_ticker("test", "nvda")
        assert "NVDA" in wm.get("test").tickers

    def test_remove_ticker(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl3.json"))
        wm.create("test", ["AAPL", "MSFT"])
        wm.remove_ticker("test", "AAPL")
        assert "AAPL" not in wm.get("test").tickers

    def test_add_ticker_no_dup(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl4.json"))
        wm.create("test", ["AAPL"])
        wm.add_ticker("test", "AAPL")
        assert wm.get("test").tickers.count("AAPL") == 1

    def test_get_signals(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl5.json"))
        wm.create("test", ["AAPL", "MSFT"])
        signals = wm.get_signals("test")
        assert len(signals) == 2
        assert signals[0]["ticker"] == "AAPL"

    def test_alerts(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl6.json"))
        wm.create("test", ["AAPL"])
        wm.add_alert("test", "AAPL", "price > 200")
        alerts = wm.get_alerts("test")
        assert len(alerts) == 1
        assert alerts[0].condition == "price > 200"

    def test_delete(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl7.json"))
        wm.create("test", [])
        assert wm.delete("test") is True
        assert wm.get("test") is None

    def test_missing_watchlist_error(self, tmp_dir):
        wm = WatchlistManager(str(tmp_dir / "wl8.json"))
        with pytest.raises(KeyError):
            wm.add_ticker("nope", "AAPL")

    def test_persistence(self, tmp_dir):
        path = str(tmp_dir / "wlp.json")
        wm1 = WatchlistManager(path)
        wm1.create("persist", ["TSLA"])
        wm1.add_alert("persist", "TSLA", "price < 100")
        wm2 = WatchlistManager(path)
        assert "TSLA" in wm2.get("persist").tickers
        assert len(wm2.get_alerts("persist")) == 1
