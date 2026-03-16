"""Tests for TradeAnalyzer."""

import os
import pytest
from datetime import datetime, timedelta
from src.analytics.trade_analyzer import TradeAnalyzer, Trade


def _sample_trades():
    base = datetime(2024, 6, 3, 9, 30)
    return [
        Trade(base, base + timedelta(hours=2), 150.0, 0.015, 'AAPL', 'long'),
        Trade(base + timedelta(days=1), base + timedelta(days=1, hours=3), -80.0, -0.008, 'MSFT', 'long'),
        Trade(base + timedelta(days=2), base + timedelta(days=2, hours=1), 200.0, 0.020, 'GOOG', 'long'),
        Trade(base + timedelta(days=3), base + timedelta(days=3, hours=4), -50.0, -0.005, 'AMZN', 'short'),
        Trade(base + timedelta(days=4), base + timedelta(days=4, hours=2), 300.0, 0.030, 'TSLA', 'long'),
        Trade(base + timedelta(days=5), base + timedelta(days=5, hours=1), 100.0, 0.010, 'NVDA', 'long'),
        Trade(base + timedelta(days=7), base + timedelta(days=7, hours=5), -120.0, -0.012, 'META', 'short'),
        Trade(base + timedelta(days=8), base + timedelta(days=8, hours=2), 50.0, 0.005, 'AAPL', 'long'),
    ]


class TestTradeAnalyzer:
    def test_analyze_basic(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['total_trades'] == 8
        assert 0 < result['win_rate'] < 1

    def test_analyze_win_rate(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        # 5 wins, 3 losses
        assert result['win_rate'] == 0.625

    def test_analyze_profit_factor(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['profit_factor'] > 1  # profitable system

    def test_analyze_expectancy(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['expectancy'] > 0

    def test_analyze_consecutive(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['max_consecutive_wins'] >= 1
        assert result['max_consecutive_losses'] >= 1

    def test_analyze_best_worst(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['best_trade']['pnl'] == 300.0
        assert result['worst_trade']['pnl'] == -120.0

    def test_analyze_by_weekday(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert isinstance(result['by_weekday'], dict)
        assert len(result['by_weekday']) > 0

    def test_analyze_by_hour(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert isinstance(result['by_hour'], dict)

    def test_analyze_by_month(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert '2024-06' in result['by_month']

    def test_analyze_empty(self):
        ta = TradeAnalyzer()
        result = ta.analyze([])
        assert result['total_trades'] == 0

    def test_analyze_all_wins(self):
        base = datetime(2024, 1, 1, 10, 0)
        trades = [Trade(base, base + timedelta(hours=1), 100.0, 0.01, 'X', 'long') for _ in range(5)]
        ta = TradeAnalyzer()
        result = ta.analyze(trades)
        assert result['win_rate'] == 1.0
        assert result['profit_factor'] == float('inf')

    def test_analyze_all_losses(self):
        base = datetime(2024, 1, 1, 10, 0)
        trades = [Trade(base, base + timedelta(hours=1), -100.0, -0.01, 'X', 'long') for _ in range(5)]
        ta = TradeAnalyzer()
        result = ta.analyze(trades)
        assert result['win_rate'] == 0.0

    def test_render_html(self, tmp_path):
        ta = TradeAnalyzer()
        ta.analyze(_sample_trades())
        out = str(tmp_path / "report.html")
        ta.render_html(out)
        assert os.path.exists(out)
        content = open(out).read()
        assert 'Trade Analysis' in content

    def test_render_html_before_analyze(self):
        ta = TradeAnalyzer()
        with pytest.raises(RuntimeError):
            ta.render_html("x.html")

    def test_total_pnl(self):
        ta = TradeAnalyzer()
        result = ta.analyze(_sample_trades())
        assert result['total_pnl'] == 550.0
