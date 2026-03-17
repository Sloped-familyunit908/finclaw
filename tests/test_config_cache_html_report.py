"""
Tests for v1.4.0 features:
- Config loading
- SQLite cache
- HTML report generator
- Enhanced CLI subcommands
- Portfolio/optimize/signal commands
"""
import json
import math
import os
import sqlite3
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══ Config Tests ═══

class TestConfig:
    def test_default_config(self):
        from src.config import FinClawConfig
        c = FinClawConfig()
        assert c.default_strategy == "momentum"
        assert c.backtest.initial_capital == 100000
        assert c.risk.max_position_pct == 0.10
        assert c.cache.backend == "sqlite"

    def test_load_missing_file(self):
        from src.config import FinClawConfig
        c = FinClawConfig.load("/nonexistent/path.yml")
        assert c.default_strategy == "momentum"

    def test_to_dict(self):
        from src.config import FinClawConfig
        c = FinClawConfig()
        d = c.to_dict()
        assert "backtest" in d
        assert "risk" in d
        assert d["backtest"]["commission"] == 0.001

    def test_custom_values(self):
        from src.config import FinClawConfig, BacktestConfig, RiskConfig
        c = FinClawConfig(
            default_strategy="soros",
            backtest=BacktestConfig(initial_capital=500000),
            risk=RiskConfig(stop_loss_pct=0.10),
        )
        assert c.default_strategy == "soros"
        assert c.backtest.initial_capital == 500000
        assert c.risk.stop_loss_pct == 0.10

    def test_load_yaml_file(self):
        from src.config import FinClawConfig
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("default_strategy: buffett\nbacktest:\n  initial_capital: 200000\n")
            f.flush()
            path = f.name
        try:
            c = FinClawConfig.load(path)
            # If yaml is available, it parses; otherwise defaults
            assert c.default_strategy in ("buffett", "momentum")
        finally:
            os.unlink(path)

    def test_config_report_section(self):
        from src.config import FinClawConfig
        c = FinClawConfig()
        assert c.report.format == "html"
        assert c.report.theme == "dark"

    def test_config_cache_section(self):
        from src.config import FinClawConfig
        c = FinClawConfig()
        assert c.cache.ttl_seconds == 3600
        assert c.cache.db_path.endswith("cache.db")


# ═══ Cache Tests ═══

class TestSQLiteCache:
    def _make_cache(self):
        from src.pipeline.cache import DataCache
        tmpdir = tempfile.mkdtemp()
        return DataCache(cache_dir=tmpdir, default_ttl=10)

    def test_set_and_get(self):
        cache = self._make_cache()
        cache.set("AAPL_5y", [{"price": 150}])
        result = cache.get("AAPL_5y")
        assert result == [{"price": 150}]

    def test_miss(self):
        cache = self._make_cache()
        assert cache.get("NONEXISTENT") is None

    def test_ttl_expiration(self):
        from src.pipeline.cache import DataCache
        tmpdir = tempfile.mkdtemp()
        cache = DataCache(cache_dir=tmpdir, default_ttl=0.1)
        cache.set("key", [{"v": 1}])
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_invalidate(self):
        cache = self._make_cache()
        cache.set("key", [{"v": 1}])
        cache.invalidate("key")
        assert cache.get("key") is None

    def test_clear(self):
        cache = self._make_cache()
        cache.set("a", [{"v": 1}])
        cache.set("b", [{"v": 2}])
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_stats(self):
        cache = self._make_cache()
        cache.set("a", [{"v": 1}])
        cache.get("a")  # hit
        cache.get("b")  # miss
        stats = cache.stats()
        assert stats.hits >= 1
        assert stats.misses >= 1
        assert stats.hit_rate > 0
        assert stats.total_entries >= 1

    def test_purge_expired(self):
        from src.pipeline.cache import DataCache
        tmpdir = tempfile.mkdtemp()
        cache = DataCache(cache_dir=tmpdir, default_ttl=0.1)
        cache.set("expired", [{"v": 1}])
        time.sleep(0.2)
        purged = cache.purge_expired()
        assert purged >= 1

    def test_keys(self):
        cache = self._make_cache()
        cache.set("AAPL", [{"p": 1}])
        cache.set("MSFT", [{"p": 2}])
        keys = cache.keys()
        assert "AAPL" in keys
        assert "MSFT" in keys

    def test_overwrite(self):
        cache = self._make_cache()
        cache.set("k", [{"v": 1}])
        cache.set("k", [{"v": 2}])
        assert cache.get("k") == [{"v": 2}]

    def test_sqlite_persistence(self):
        """Data survives memory clear if in SQLite."""
        cache = self._make_cache()
        cache.set("persist", [{"v": 42}])
        cache._memory.clear()  # Clear memory cache
        result = cache.get("persist")
        assert result == [{"v": 42}]

    def test_custom_ttl(self):
        cache = self._make_cache()
        cache.set("short", [{"v": 1}], ttl=0.1)
        assert cache.get("short") is not None
        time.sleep(0.2)
        assert cache.get("short") is None


# ═══ HTML Report Tests ═══

class TestHTMLReport:
    def _sample_report(self):
        return {
            "total_return": 0.35,
            "annualized_return": 0.12,
            "sharpe_ratio": 1.5,
            "sortino_ratio": 2.0,
            "max_drawdown": 0.15,
            "win_rate": 0.55,
            "profit_factor": 1.8,
            "num_trades": 42,
            "avg_trade_return": 0.008,
            "avg_win": 0.025,
            "avg_loss": -0.015,
            "equity_curve": [1.0 + i * 0.005 for i in range(100)],
            "monthly_returns": [
                {"month": m, "year": 0, "return_pct": 0.02 * (1 if m % 2 else -0.5)}
                for m in range(1, 13)
            ],
            "trade_log": [
                {"entry_idx": i*10, "exit_idx": i*10+5,
                 "entry_price": 100+i, "exit_price": 102+i,
                 "pnl_pct": 0.02, "holding_period": 5}
                for i in range(10)
            ],
        }

    def test_generate_html(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report())
        assert "<!DOCTYPE html>" in html
        assert "FinClaw" in html
        assert "Equity Curve" in html

    def test_contains_metrics(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report())
        assert "35.0%" in html or "+35.0%" in html
        assert "1.50" in html  # sharpe
        assert "42" in html  # trades

    def test_contains_svg(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report())
        assert "<svg" in html
        assert "polyline" in html

    def test_write_to_file(self):
        from src.reports.html_report import generate_html_report
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            html = generate_html_report(self._sample_report(), output_path=path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000
        finally:
            os.unlink(path)

    def test_empty_data(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report({})
        assert "<!DOCTYPE html>" in html

    def test_heatmap_present(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report())
        assert "Monthly Returns" in html
        assert "Jan" in html

    def test_trade_log_table(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report())
        assert "Trade Log" in html
        assert "$100" in html or "100.00" in html

    def test_benchmark_metrics(self):
        from src.reports.html_report import generate_html_report
        data = self._sample_report()
        data["benchmark_return"] = 0.10
        data["alpha"] = 0.05
        html = generate_html_report(data)
        assert "Benchmark" in html
        assert "Alpha" in html

    def test_custom_title(self):
        from src.reports.html_report import generate_html_report
        html = generate_html_report(self._sample_report(), title="Custom Report")
        assert "Custom Report" in html


# ═══ CLI Tests ═══

class TestCLI:
    def test_info_command(self):
        """info command should not crash."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "finclaw.py", "info"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "FinClaw" in result.stdout

    def test_help_command(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "finclaw.py", "--help"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "backtest" in result.stdout
        assert "signal" in result.stdout
        assert "optimize" in result.stdout
        assert "portfolio" in result.stdout

    def test_cache_stats(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "finclaw.py", "cache", "--stats"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "Cache" in result.stdout


# ═══ SVG Chart Tests ═══

class TestSVGCharts:
    def test_line_chart(self):
        from src.reports.html_report import _svg_line_chart
        svg = _svg_line_chart([1.0, 1.5, 1.3, 1.8, 2.0])
        assert "<svg" in svg
        assert "polyline" in svg

    def test_line_chart_empty(self):
        from src.reports.html_report import _svg_line_chart
        result = _svg_line_chart([])
        assert "No data" in result

    def test_line_chart_single(self):
        from src.reports.html_report import _svg_line_chart
        result = _svg_line_chart([1.0])
        assert "No data" in result

    def test_monthly_heatmap(self):
        from src.reports.html_report import _monthly_heatmap
        data = [{"month": m, "year": 0, "return_pct": 0.01} for m in range(1, 4)]
        html = _monthly_heatmap(data)
        assert "Jan" in html
        assert "heatmap" in html

    def test_monthly_heatmap_empty(self):
        from src.reports.html_report import _monthly_heatmap
        result = _monthly_heatmap([])
        assert "No monthly" in result


# ═══ Strategy Mapping Tests ═══

class TestStrategies:
    def test_all_strategies_have_required_keys(self):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Import from the CLI module
        from finclaw import STRATEGIES
        for name, s in STRATEGIES.items():
            assert "desc" in s, f"{name} missing desc"
            assert "select" in s, f"{name} missing select"
            assert "alloc" in s, f"{name} missing alloc"
            assert callable(s["select"]), f"{name} select not callable"

    def test_momentum_strategy_exists(self):
        from finclaw import STRATEGIES
        assert "momentum" in STRATEGIES

    def test_mean_reversion_strategy_exists(self):
        from finclaw import STRATEGIES
        assert "mean_reversion" in STRATEGIES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
