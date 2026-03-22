"""Tests for AKShare enhanced adapter."""

import pytest


class TestAKShareEnhancedFunctions:
    """Test that all AKShare enhanced functions exist and handle errors gracefully."""

    def test_get_realtime_quotes_exists(self):
        """Function should be importable."""
        from src.exchanges.akshare_enhanced import get_realtime_quotes
        assert callable(get_realtime_quotes)

    def test_get_stock_fundamentals_exists(self):
        """Function should be importable."""
        from src.exchanges.akshare_enhanced import get_stock_fundamentals
        assert callable(get_stock_fundamentals)

    def test_get_fund_flow_exists(self):
        """Function should be importable."""
        from src.exchanges.akshare_enhanced import get_fund_flow
        assert callable(get_fund_flow)

    def test_get_north_bound_flow_exists(self):
        """Function should be importable."""
        from src.exchanges.akshare_enhanced import get_north_bound_flow
        assert callable(get_north_bound_flow)

    def test_get_realtime_quotes_returns_list(self):
        """get_realtime_quotes should always return a list (even on error)."""
        from src.exchanges.akshare_enhanced import get_realtime_quotes
        result = get_realtime_quotes(symbols=['999999'])  # non-existent code
        assert isinstance(result, list)

    def test_get_stock_fundamentals_returns_dict(self):
        """get_stock_fundamentals should always return a dict (even on error)."""
        from src.exchanges.akshare_enhanced import get_stock_fundamentals
        result = get_stock_fundamentals('999999')  # non-existent code
        assert isinstance(result, dict)

    def test_get_fund_flow_returns_dict(self):
        """get_fund_flow should always return a dict (even on error)."""
        from src.exchanges.akshare_enhanced import get_fund_flow
        result = get_fund_flow('999999')  # non-existent code
        assert isinstance(result, dict)

    def test_get_north_bound_flow_returns_dict(self):
        """get_north_bound_flow should always return a dict (even on error)."""
        from src.exchanges.akshare_enhanced import get_north_bound_flow
        result = get_north_bound_flow()
        assert isinstance(result, dict)


class TestAKShareGracefulDegradation:
    """Test that functions degrade gracefully when akshare is not available."""

    def test_graceful_on_import_error(self):
        """Functions should catch import errors inside try/except."""
        # The module itself imports fine (no top-level akshare import)
        import src.exchanges.akshare_enhanced as mod
        # All functions exist regardless of akshare availability
        assert hasattr(mod, 'get_realtime_quotes')
        assert hasattr(mod, 'get_stock_fundamentals')
        assert hasattr(mod, 'get_fund_flow')
        assert hasattr(mod, 'get_north_bound_flow')

    def test_module_has_no_toplevel_akshare_import(self):
        """The module should not import akshare at the top level."""
        import inspect
        import src.exchanges.akshare_enhanced as mod
        source = inspect.getsource(mod)
        # Check that 'import akshare' only appears inside function bodies
        lines = source.split('\n')
        toplevel_imports = [
            line for line in lines
            if 'import akshare' in line
            and not line.strip().startswith('#')
            and line[0:1] not in (' ', '\t')  # not indented = top-level
        ]
        assert len(toplevel_imports) == 0, (
            f"Found top-level akshare import(s): {toplevel_imports}"
        )
