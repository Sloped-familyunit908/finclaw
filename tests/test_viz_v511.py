"""Tests for FinClaw Terminal Visualization v5.11.0

40+ tests covering charts, dashboard, report visualizer, and CLI integration.
"""

import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.viz.charts import TerminalChart
from src.viz.dashboard import PortfolioDashboard
from src.viz.report import BacktestVisualizer, BacktestResult


# ═══════════════════════════════════════════════════════════════
# TerminalChart.candlestick
# ═══════════════════════════════════════════════════════════════

class TestCandlestick:
    def _sample_data(self, n=10):
        import random
        random.seed(42)
        data = []
        price = 100.0
        for _ in range(n):
            o = price
            c = o + random.uniform(-3, 3)
            h = max(o, c) + random.uniform(0, 2)
            l = min(o, c) - random.uniform(0, 2)
            data.append({"open": o, "high": h, "low": l, "close": c})
            price = c
        return data

    def test_basic_render(self):
        out = TerminalChart.candlestick(self._sample_data())
        assert "│" in out or "┃" in out

    def test_empty_data(self):
        assert TerminalChart.candlestick([]) == "(no data)"

    def test_single_candle(self):
        data = [{"open": 100, "high": 105, "low": 95, "close": 102}]
        out = TerminalChart.candlestick(data)
        assert len(out) > 0

    def test_flat_market(self):
        data = [{"open": 100, "high": 100, "low": 100, "close": 100}] * 5
        out = TerminalChart.candlestick(data)
        assert len(out) > 0

    def test_custom_dimensions(self):
        out = TerminalChart.candlestick(self._sample_data(), width=40, height=10)
        lines = out.split("\n")
        assert len(lines) >= 10

    def test_many_candles_truncated(self):
        data = self._sample_data(200)
        out = TerminalChart.candlestick(data, width=60)
        assert len(out) > 0  # Should not crash, truncates to fit

    def test_green_red_colors(self):
        data = [
            {"open": 100, "high": 110, "low": 95, "close": 105},  # green
            {"open": 105, "high": 106, "low": 98, "close": 99},   # red
        ]
        out = TerminalChart.candlestick(data)
        assert "\033[32m" in out  # green
        assert "\033[31m" in out  # red


# ═══════════════════════════════════════════════════════════════
# TerminalChart.line
# ═══════════════════════════════════════════════════════════════

class TestLineChart:
    def test_basic_render(self):
        values = [math.sin(x / 10) for x in range(100)]
        out = TerminalChart.line(values)
        assert "│" in out
        assert len(out.split("\n")) > 5

    def test_empty(self):
        assert TerminalChart.line([]) == "(no data)"

    def test_single_value(self):
        out = TerminalChart.line([42.0])
        assert len(out) > 0

    def test_constant_values(self):
        out = TerminalChart.line([5.0] * 50)
        assert len(out) > 0

    def test_with_label(self):
        out = TerminalChart.line([1, 2, 3], label="Test")
        assert "Test" in out

    def test_custom_size(self):
        out = TerminalChart.line([1, 2, 3, 4, 5], width=40, height=8)
        lines = out.split("\n")
        assert len(lines) >= 8

    def test_negative_values(self):
        out = TerminalChart.line([-5, -3, -1, -4, -2])
        assert len(out) > 0

    def test_large_range(self):
        out = TerminalChart.line([0.001, 1000000])
        assert len(out) > 0


# ═══════════════════════════════════════════════════════════════
# TerminalChart.bar
# ═══════════════════════════════════════════════════════════════

class TestBarChart:
    def test_basic(self):
        out = TerminalChart.bar(["A", "B", "C"], [10, 20, 15])
        assert "█" in out
        assert "A" in out

    def test_empty(self):
        assert TerminalChart.bar([], []) == "(no data)"

    def test_negative_values(self):
        out = TerminalChart.bar(["Win", "Loss"], [500, -300])
        assert "\033[31m" in out  # red for negative

    def test_all_zero(self):
        out = TerminalChart.bar(["X", "Y"], [0, 0])
        assert len(out) > 0

    def test_single_bar(self):
        out = TerminalChart.bar(["Solo"], [42])
        assert "Solo" in out


# ═══════════════════════════════════════════════════════════════
# TerminalChart.heatmap
# ═══════════════════════════════════════════════════════════════

class TestHeatmap:
    def test_basic(self):
        matrix = [[1.0, 0.5], [0.5, 1.0]]
        out = TerminalChart.heatmap(matrix, ["A", "B"], ["X", "Y"])
        assert "│" in out

    def test_empty(self):
        assert TerminalChart.heatmap([], [], []) == "(no data)"

    def test_correlation_matrix(self):
        matrix = [
            [1.0, 0.8, -0.3],
            [0.8, 1.0, 0.1],
            [-0.3, 0.1, 1.0],
        ]
        out = TerminalChart.heatmap(matrix, ["A", "B", "C"], ["A", "B", "C"])
        assert len(out.split("\n")) >= 3

    def test_single_cell(self):
        out = TerminalChart.heatmap([[0.5]], ["X"], ["Y"])
        assert len(out) > 0


# ═══════════════════════════════════════════════════════════════
# TerminalChart.histogram
# ═══════════════════════════════════════════════════════════════

class TestHistogram:
    def test_basic(self):
        import random
        random.seed(42)
        vals = [random.gauss(0, 1) for _ in range(1000)]
        out = TerminalChart.histogram(vals)
        assert "█" in out
        assert "n=1000" in out

    def test_empty(self):
        assert TerminalChart.histogram([]) == "(no data)"

    def test_all_same(self):
        out = TerminalChart.histogram([5.0] * 100)
        assert "5" in out

    def test_custom_bins(self):
        vals = list(range(100))
        out = TerminalChart.histogram(vals, bins=5)
        lines = [l for l in out.split("\n") if "│" in l]
        assert len(lines) == 5


# ═══════════════════════════════════════════════════════════════
# TerminalChart.sparkline
# ═══════════════════════════════════════════════════════════════

class TestSparkline:
    def test_basic(self):
        out = TerminalChart.sparkline([1, 3, 2, 5, 4])
        assert len(out) == 5

    def test_empty(self):
        assert TerminalChart.sparkline([]) == ""

    def test_constant(self):
        out = TerminalChart.sparkline([5, 5, 5])
        assert len(out) == 3

    def test_two_values(self):
        out = TerminalChart.sparkline([0, 100])
        assert out[0] == "▁"
        assert out[1] == "█"


# ═══════════════════════════════════════════════════════════════
# PortfolioDashboard
# ═══════════════════════════════════════════════════════════════

class TestPortfolioDashboard:
    def _sample_portfolio(self):
        return {
            "total_value": 125430,
            "total_cost": 120000,
            "holdings": [
                {"symbol": "AAPL", "weight": 0.45, "pnl_pct": 2.3},
                {"symbol": "MSFT", "weight": 0.30, "pnl_pct": -0.5},
                {"symbol": "GOOGL", "weight": 0.25, "pnl_pct": 1.1},
            ],
            "history": [120000, 121000, 119500, 122000, 124000, 123500, 125430],
        }

    def test_render(self):
        dash = PortfolioDashboard()
        out = dash.render(self._sample_portfolio())
        assert "Portfolio" in out
        assert "AAPL" in out
        assert "█" in out

    def test_box_drawing(self):
        dash = PortfolioDashboard()
        out = dash.render(self._sample_portfolio())
        assert "┌" in out
        assert "└" in out
        assert "├" in out

    def test_empty_portfolio(self):
        dash = PortfolioDashboard()
        out = dash.render({"total_value": 0, "total_cost": 0, "holdings": [], "history": []})
        assert "Portfolio" in out

    def test_loss_portfolio(self):
        dash = PortfolioDashboard()
        pf = self._sample_portfolio()
        pf["total_value"] = 110000
        out = dash.render(pf)
        assert "\033[31m" in out  # red for loss... wait cost > value

    def test_no_history(self):
        dash = PortfolioDashboard()
        pf = self._sample_portfolio()
        pf.pop("history")
        out = dash.render(pf)
        assert "Portfolio" in out


# ═══════════════════════════════════════════════════════════════
# BacktestVisualizer
# ═══════════════════════════════════════════════════════════════

class TestBacktestVisualizer:
    def _sample_result(self):
        curve = [10000 + i * 10 + (i % 7) * 50 - (i % 3) * 30 for i in range(252)]
        return BacktestResult(
            total_return=0.15,
            cagr=0.12,
            sharpe=1.5,
            sortino=2.0,
            max_drawdown=0.08,
            win_rate=0.55,
            profit_factor=1.8,
            num_trades=42,
            equity_curve=curve,
            monthly_returns={
                "2024-01": 0.02, "2024-02": -0.01, "2024-03": 0.03,
                "2024-04": 0.01, "2024-05": 0.02, "2024-06": -0.005,
                "2024-07": 0.015, "2024-08": 0.025, "2024-09": -0.01,
                "2024-10": 0.02, "2024-11": 0.01, "2024-12": 0.03,
            },
            trades=[
                {"pnl": 100}, {"pnl": -50}, {"pnl": 200}, {"pnl": -30},
                {"pnl": 150}, {"pnl": -80}, {"pnl": 300},
            ],
            initial_capital=10000,
            final_equity=11500,
        )

    def test_equity_curve(self):
        viz = BacktestVisualizer()
        out = viz.equity_curve(self._sample_result())
        assert "Equity" in out

    def test_drawdown_chart(self):
        viz = BacktestVisualizer()
        out = viz.drawdown_chart(self._sample_result())
        assert "Drawdown" in out

    def test_monthly_heatmap(self):
        viz = BacktestVisualizer()
        out = viz.monthly_returns_heatmap(self._sample_result())
        assert "2024" in out

    def test_trade_scatter(self):
        viz = BacktestVisualizer()
        out = viz.trade_scatter(self._sample_result())
        assert "T1" in out

    def test_full_report(self):
        viz = BacktestVisualizer()
        out = viz.full_report(self._sample_result())
        assert "BACKTEST REPORT" in out
        assert "Sharpe" in out
        assert "Equity" in out

    def test_empty_result(self):
        viz = BacktestVisualizer()
        result = BacktestResult()
        out = viz.full_report(result)
        assert "BACKTEST REPORT" in out

    def test_equity_curve_empty(self):
        viz = BacktestVisualizer()
        assert "(no equity data)" in viz.equity_curve(BacktestResult())

    def test_drawdown_insufficient(self):
        viz = BacktestVisualizer()
        assert "(insufficient data)" in viz.drawdown_chart(BacktestResult(equity_curve=[100]))

    def test_monthly_empty(self):
        viz = BacktestVisualizer()
        assert "(no monthly data)" in viz.monthly_returns_heatmap(BacktestResult())

    def test_trades_empty(self):
        viz = BacktestVisualizer()
        assert "(no trades)" in viz.trade_scatter(BacktestResult())


# ═══════════════════════════════════════════════════════════════
# CLI integration
# ═══════════════════════════════════════════════════════════════

class TestCLIChart:
    def test_chart_parser(self):
        # cli.py is a module file alongside cli/ package — import directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("cli_main", os.path.join(os.path.dirname(__file__), "..", "src", "cli", "main.py"))
        cli_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_mod)
        parser = cli_mod.build_parser()
        args = parser.parse_args(["chart", "AAPL", "--type", "line", "--period", "1y"])
        assert args.command == "chart"
        assert args.symbol == "AAPL"
        assert args.type == "line"
        assert args.period == "1y"

    def test_chart_candle_parser(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("cli_main", os.path.join(os.path.dirname(__file__), "..", "src", "cli", "main.py"))
        cli_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_mod)
        parser = cli_mod.build_parser()
        args = parser.parse_args(["chart", "BTCUSDT", "--type", "candle", "--period", "30d"])
        assert args.type == "candle"

    def test_chart_default_type(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("cli_main", os.path.join(os.path.dirname(__file__), "..", "src", "cli", "main.py"))
        cli_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli_mod)
        parser = cli_mod.build_parser()
        args = parser.parse_args(["chart", "MSFT"])
        assert args.type == "line"
        assert args.width == 80
        assert args.height == 20
