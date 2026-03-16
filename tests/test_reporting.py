"""
Tests for src/reporting/ — v4.7.0
35+ tests covering html_report, tearsheet, comparison, and CLI integration.
"""

import json
import math
import os
import tempfile
import pytest

from src.reporting.html_report import (
    BacktestReportGenerator,
    BacktestResult,
    _svg_line_chart,
    _svg_bar_chart,
    _svg_scatter,
    _svg_histogram,
    _metric_card,
    _monthly_heatmap,
    _trade_log_table,
    _risk_metrics_table,
)
from src.reporting.tearsheet import (
    Tearsheet,
    _cumulative,
    _rolling_sharpe,
    _rolling_vol,
    _underwater,
    _worst_drawdowns,
    _monthly_table,
    _annual_returns,
)
from src.reporting.comparison import StrategyComparison, _calc_metrics


# ─── Fixtures ───────────────────────────────────────────────────

def _sample_returns(n=500, seed=42):
    """Deterministic pseudo-random returns."""
    import random
    rng = random.Random(seed)
    return [rng.gauss(0.0003, 0.01) for _ in range(n)]


def _sample_result() -> BacktestResult:
    rets = _sample_returns(300)
    eq = [100000.0]
    for r in rets:
        eq.append(eq[-1] * (1 + r))
    monthly = [
        {"year": 2024, "month": m, "return_pct": 0.02 * (1 if m % 2 else -1)}
        for m in range(1, 13)
    ]
    trades = [
        {"entry_date": "2024-01-01", "exit_date": "2024-01-10", "entry_price": 100, "exit_price": 110, "pnl_pct": 0.10, "holding_days": 10},
        {"entry_date": "2024-02-01", "exit_date": "2024-02-05", "entry_price": 110, "exit_price": 105, "pnl_pct": -0.045, "holding_days": 5},
        {"entry_date": "2024-03-01", "exit_date": "2024-03-20", "entry_price": 105, "exit_price": 120, "pnl_pct": 0.143, "holding_days": 20},
    ]
    return BacktestResult(
        total_return=0.15,
        annualized_return=0.12,
        sharpe_ratio=1.5,
        sortino_ratio=2.1,
        max_drawdown=0.08,
        win_rate=0.6,
        profit_factor=1.8,
        num_trades=3,
        avg_trade_return=0.066,
        avg_win=0.12,
        avg_loss=-0.045,
        equity_curve=eq,
        monthly_returns=monthly,
        trade_log=trades,
        positions=[1.0] * 150 + [0.5] * 150,
        strategy_name="TestStrategy",
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )


# ─── BacktestResult tests ──────────────────────────────────────

class TestBacktestResult:
    def test_default(self):
        r = BacktestResult()
        assert r.total_return == 0.0
        assert r.equity_curve == []

    def test_to_dict(self):
        r = _sample_result()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert d["total_return"] == 0.15
        assert d["strategy_name"] == "TestStrategy"

    def test_from_dict(self):
        d = {"total_return": 0.25, "sharpe_ratio": 1.8, "unknown_field": 99}
        r = BacktestResult.from_dict(d)
        assert r.total_return == 0.25
        assert r.sharpe_ratio == 1.8

    def test_roundtrip(self):
        r = _sample_result()
        d = r.to_dict()
        r2 = BacktestResult.from_dict(d)
        assert r2.total_return == r.total_return
        assert len(r2.equity_curve) == len(r.equity_curve)


# ─── SVG chart tests ───────────────────────────────────────────

class TestSVGCharts:
    def test_line_chart_basic(self):
        svg = _svg_line_chart([1, 2, 3, 4, 5])
        assert "<svg" in svg
        assert "polyline" in svg

    def test_line_chart_empty(self):
        result = _svg_line_chart([])
        assert "Insufficient" in result

    def test_line_chart_single(self):
        result = _svg_line_chart([5.0])
        assert "Insufficient" in result

    def test_line_chart_title(self):
        svg = _svg_line_chart([1, 2, 3], title="Test")
        assert "Test" in svg

    def test_line_chart_zero_line(self):
        svg = _svg_line_chart([-1, 0, 1], show_zero=True)
        assert "stroke-dasharray" in svg

    def test_bar_chart(self):
        svg = _svg_bar_chart(["A", "B", "C"], [10, -5, 15])
        assert "<svg" in svg
        assert "rect" in svg

    def test_bar_chart_empty(self):
        result = _svg_bar_chart([], [])
        assert "No data" in result

    def test_scatter(self):
        svg = _svg_scatter([1, 2, 3], [1.1, 1.9, 3.2])
        assert "<svg" in svg
        assert "circle" in svg

    def test_scatter_empty(self):
        result = _svg_scatter([], [])
        assert "No scatter" in result

    def test_histogram(self):
        svg = _svg_histogram([0.01, -0.02, 0.03, -0.01, 0.005] * 10)
        assert "<svg" in svg
        assert "rect" in svg

    def test_histogram_empty(self):
        result = _svg_histogram([])
        assert "No data" in result


# ─── HTML component tests ──────────────────────────────────────

class TestHTMLComponents:
    def test_metric_card(self):
        card = _metric_card("Return", "+15%", "#00e676")
        assert "Return" in card
        assert "+15%" in card

    def test_monthly_heatmap(self):
        m = [{"year": 2024, "month": i, "return_pct": 0.01 * i} for i in range(1, 13)]
        hm = _monthly_heatmap(m)
        assert "2024" in hm
        assert "Jan" in hm

    def test_monthly_heatmap_empty(self):
        assert "No monthly" in _monthly_heatmap([])

    def test_trade_log(self):
        trades = [{"entry_date": "2024-01-01", "exit_date": "2024-01-10", "entry_price": 100, "exit_price": 110, "pnl_pct": 0.1, "holding_days": 10}]
        tbl = _trade_log_table(trades)
        assert "110.00" in tbl

    def test_trade_log_empty(self):
        assert "No trades" in _trade_log_table([])

    def test_risk_metrics_table(self):
        r = _sample_result()
        tbl = _risk_metrics_table(r)
        assert "Sharpe" in tbl
        assert "1.500" in tbl


# ─── BacktestReportGenerator tests ────────────────────────────

class TestBacktestReportGenerator:
    def test_generate_html(self):
        r = _sample_result()
        gen = BacktestReportGenerator(r)
        html = gen.generate_html()
        assert "<!DOCTYPE html>" in html
        assert "Executive Summary" in html
        assert "Equity Curve" in html
        assert "Drawdown" in html
        assert "Monthly Returns" in html
        assert "Trade Analysis" in html
        assert "Risk Metrics" in html
        assert "Position Sizing" in html
        assert "Trade Log" in html
        assert "v4.9.0" in html

    def test_generate_from_dict(self):
        d = _sample_result().to_dict()
        gen = BacktestReportGenerator(d)
        html = gen.generate_html()
        assert "<!DOCTYPE html>" in html

    def test_output_to_file(self, tmp_path):
        r = _sample_result()
        gen = BacktestReportGenerator(r)
        out = str(tmp_path / "report.html")
        gen.generate_html(output_path=out)
        assert os.path.exists(out)
        content = open(out, encoding="utf-8").read()
        assert "<!DOCTYPE html>" in content

    def test_empty_result(self):
        gen = BacktestReportGenerator(BacktestResult())
        html = gen.generate_html()
        assert "<!DOCTYPE html>" in html

    def test_no_positions(self):
        r = _sample_result()
        r.positions = []
        gen = BacktestReportGenerator(r)
        html = gen.generate_html()
        assert "Position Sizing" not in html


# ─── Tearsheet tests ──────────────────────────────────────────

class TestTearsheet:
    def test_generate_basic(self):
        rets = _sample_returns(500)
        html = Tearsheet.generate(rets)
        assert "<!DOCTYPE html>" in html
        assert "Cumulative Returns" in html
        assert "Rolling Sharpe" in html
        assert "Underwater" in html
        assert "Monthly Returns" in html
        assert "Annual Returns" in html
        assert "Distribution" in html
        assert "Worst Drawdowns" in html

    def test_with_benchmark(self):
        rets = _sample_returns(300, seed=1)
        bench = _sample_returns(300, seed=2)
        html = Tearsheet.generate(rets, benchmark=bench)
        assert "Benchmark" in html

    def test_output_file(self, tmp_path):
        rets = _sample_returns(200)
        out = str(tmp_path / "tear.html")
        Tearsheet.generate(rets, output_path=out)
        assert os.path.exists(out)

    def test_cumulative(self):
        cum = _cumulative([0.1, -0.05, 0.03])
        assert len(cum) == 4
        assert cum[0] == 1.0
        assert abs(cum[1] - 1.1) < 1e-10

    def test_rolling_sharpe(self):
        rets = _sample_returns(200)
        rs = _rolling_sharpe(rets, window=50)
        assert len(rs) == 200
        assert rs[0] is None
        assert rs[49] is not None

    def test_rolling_vol(self):
        rets = _sample_returns(100)
        rv = _rolling_vol(rets, window=20)
        assert rv[19] is not None
        assert rv[0] is None

    def test_underwater(self):
        uw = _underwater([0.1, -0.05, 0.03])
        assert uw[0] == 0  # starts at 0
        assert any(u < 0 for u in uw)

    def test_worst_drawdowns(self):
        rets = [0.01] * 50 + [-0.05] * 10 + [0.01] * 50
        dds = _worst_drawdowns(rets, top_n=3)
        assert len(dds) >= 1
        assert dds[0]["depth"] < 0

    def test_monthly_table(self):
        rets = _sample_returns(100)
        mt = _monthly_table(rets)
        assert len(mt) > 0
        assert "year" in mt[0]

    def test_annual_returns(self):
        rets = _sample_returns(500)
        ar = _annual_returns(rets)
        assert len(ar) >= 1


# ─── Comparison tests ─────────────────────────────────────────

class TestStrategyComparison:
    def test_add_and_compare(self):
        comp = StrategyComparison()
        comp.add_strategy("A", _sample_returns(200, seed=1))
        comp.add_strategy("B", _sample_returns(200, seed=2))
        result = comp.compare()
        assert len(result["strategies"]) == 2
        assert result["best_overall"] in ("A", "B")

    def test_compare_metrics(self):
        comp = StrategyComparison()
        comp.add_strategy("Bull", _sample_returns(200, seed=100))
        comp.add_strategy("Bear", [-0.01 + 0.001 * (i % 5) for i in range(200)])
        result = comp.compare()
        assert len(result["strategies"]) == 2
        assert result["best_overall"] in ("Bull", "Bear")

    def test_generate_report(self):
        comp = StrategyComparison()
        comp.add_strategy("X", _sample_returns(200, seed=10))
        comp.add_strategy("Y", _sample_returns(200, seed=20))
        comp.add_strategy("Z", _sample_returns(200, seed=30))
        html = comp.generate_report()
        assert "<!DOCTYPE html>" in html
        assert "Equity Curves" in html
        assert "Performance Metrics" in html

    def test_report_to_file(self, tmp_path):
        comp = StrategyComparison()
        comp.add_strategy("S1", _sample_returns(100))
        out = str(tmp_path / "comp.html")
        comp.generate_report(output_path=out)
        assert os.path.exists(out)

    def test_single_strategy(self):
        comp = StrategyComparison()
        comp.add_strategy("Only", _sample_returns(100))
        result = comp.compare()
        assert result["best_overall"] == "Only"


class TestCalcMetrics:
    def test_positive_returns(self):
        m = _calc_metrics(_sample_returns(252, seed=77))
        assert m["total_return"] != 0
        assert "sharpe_ratio" in m
        assert m["max_drawdown"] >= 0

    def test_negative_returns(self):
        m = _calc_metrics([-0.01] * 100)
        assert m["total_return"] < 0
        assert m["max_drawdown"] > 0

    def test_empty(self):
        assert _calc_metrics([]) == {}

    def test_mixed(self):
        m = _calc_metrics(_sample_returns(252))
        assert "volatility" in m
        assert "calmar_ratio" in m
        assert "win_rate" in m


# ─── CLI integration tests ────────────────────────────────────

class TestCLI:
    def test_tearsheet_command(self, tmp_path):
        # Create returns CSV
        csv_file = str(tmp_path / "returns.csv")
        with open(csv_file, "w") as f:
            for r in _sample_returns(100):
                f.write(f"2024-01-01,{r}\n")

        out = str(tmp_path / "out.html")
        from src.cli import main
        main(["tearsheet", "--returns", csv_file, "--output", out])
        assert os.path.exists(out)

    def test_compare_command(self, tmp_path):
        files = []
        for i, seed in enumerate([1, 2, 3]):
            fp = str(tmp_path / f"strat{i}.json")
            data = {"name": f"Strategy{i}", "returns": _sample_returns(100, seed=seed)}
            with open(fp, "w") as f:
                json.dump(data, f)
            files.append(fp)

        out = str(tmp_path / "comp.html")
        from src.cli import main
        main(["compare", "--strategies"] + files + ["--output", out])
        assert os.path.exists(out)

    def test_report_command(self, tmp_path):
        r = _sample_result()
        fp = str(tmp_path / "result.json")
        with open(fp, "w") as f:
            json.dump(r.to_dict(), f)

        out = str(tmp_path / "report.html")
        from src.cli import main
        main(["report", "--input", fp, "--output", out])
        assert os.path.exists(out)
