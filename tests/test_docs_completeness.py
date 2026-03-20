"""Tests for Issue #3: API documentation completeness — extended.

Validates that all major modules have corresponding documentation
in the docs/ directory, and that key modules have proper docstrings.
"""

import importlib
import inspect
import os
import re

import pytest


FINCLAW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(FINCLAW_ROOT, "docs")


class TestDocsDirectoryCompleteness:
    """Verify all major features have documentation pages."""

    def test_getting_started_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "getting-started.md"))

    def test_api_reference_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "api-reference.md"))

    def test_cli_reference_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "cli-reference.md"))

    def test_backtesting_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "backtesting.md"))

    def test_strategies_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "strategies.md"))

    def test_mcp_server_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "mcp-server.md"))

    def test_exchanges_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "exchanges.md"))

    def test_data_pipeline_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "data-pipeline.md"))

    def test_portfolio_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "portfolio.md"))

    def test_live_trading_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "live-trading.md"))

    def test_plugins_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "plugins.md"))

    def test_faq_doc(self):
        assert os.path.exists(os.path.join(DOCS_DIR, "faq.md"))

    def test_evolution_doc(self):
        """Evolution engine should have documentation."""
        assert os.path.exists(os.path.join(DOCS_DIR, "evolution.md"))

    def test_notifications_doc(self):
        """Notification channels should have documentation."""
        assert os.path.exists(os.path.join(DOCS_DIR, "notifications.md"))

    def test_docker_deployment_doc(self):
        """Docker/deployment should have documentation."""
        assert os.path.exists(os.path.join(DOCS_DIR, "deployment.md"))


class TestDocsContent:
    """Verify documentation content quality."""

    def test_api_reference_covers_strategies(self):
        path = os.path.join(DOCS_DIR, "api-reference.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Strategy" in content

    def test_api_reference_covers_risk(self):
        path = os.path.join(DOCS_DIR, "api-reference.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Risk" in content

    def test_api_reference_covers_backtesting(self):
        path = os.path.join(DOCS_DIR, "api-reference.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Backtest" in content

    def test_api_reference_covers_indicators(self):
        path = os.path.join(DOCS_DIR, "api-reference.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "rsi" in content.lower() or "RSI" in content

    def test_api_reference_covers_ml(self):
        path = os.path.join(DOCS_DIR, "api-reference.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Machine Learning" in content or "ML" in content

    def test_evolution_doc_has_usage(self):
        path = os.path.join(DOCS_DIR, "evolution.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "python" in content.lower() or "```" in content

    def test_notifications_doc_has_channels(self):
        path = os.path.join(DOCS_DIR, "notifications.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        # Should mention at least some notification channels
        assert "telegram" in content.lower() or "discord" in content.lower()


class TestModuleDocstrings:
    """Verify key modules have module-level docstrings."""

    @pytest.mark.parametrize("module_name", [
        "src.ta",
        "src.risk.risk_metrics",
        "src.risk.var_calculator",
        "src.data.prices",
        "src.data.cache",
        "src.mcp.server",
        "src.api.server",
        "src.strategies.mean_reversion",
        "src.strategies.trend_following",
        "src.evolution.engine",
        "src.notifications.hub",
    ])
    def test_module_has_docstring(self, module_name):
        mod = importlib.import_module(module_name)
        assert mod.__doc__, f"{module_name} missing module-level docstring"

    @pytest.mark.parametrize("module_name,class_name", [
        ("src.risk.advanced_metrics", "AdvancedRiskMetrics"),
        ("src.risk.var_calculator", "VaRCalculator"),
        ("src.risk.position_sizer", "PositionSizer"),
        ("src.strategies.mean_reversion", "MeanReversionStrategy"),
        ("src.strategies.trend_following", "TrendFollowingStrategy"),
    ])
    def test_class_has_docstring(self, module_name, class_name):
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        assert cls.__doc__, f"{module_name}.{class_name} missing class docstring"
