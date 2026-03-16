"""Tests for DrawdownAnalyzer."""

import pytest
from src.analytics.drawdown import DrawdownAnalyzer, DrawdownPeriod


class TestDrawdownAnalyzer:
    def setup_method(self):
        self.da = DrawdownAnalyzer()

    def test_max_drawdown_simple(self):
        curve = [100, 110, 105, 90, 95, 100, 108]
        result = self.da.max_drawdown(curve)
        assert result['max_dd'] < 0
        assert result['trough_value'] == 90
        assert result['peak_value'] == 110

    def test_max_drawdown_no_drawdown(self):
        curve = [100, 101, 102, 103]
        result = self.da.max_drawdown(curve)
        assert result['max_dd'] == 0.0

    def test_max_drawdown_single_point(self):
        result = self.da.max_drawdown([100])
        assert result['max_dd'] == 0.0

    def test_max_drawdown_empty(self):
        result = self.da.max_drawdown([])
        assert result['max_dd'] == 0.0

    def test_max_drawdown_value(self):
        curve = [100, 120, 60, 80]  # 50% drawdown from 120 to 60
        result = self.da.max_drawdown(curve)
        assert abs(result['max_dd'] - (-0.5)) < 0.001

    def test_drawdown_periods_basic(self):
        curve = [100, 110, 100, 90, 95, 110, 115, 100, 115]
        periods = self.da.drawdown_periods(curve)
        assert len(periods) >= 1
        assert all(isinstance(p, DrawdownPeriod) for p in periods)

    def test_drawdown_periods_recovery(self):
        curve = [100, 110, 90, 110, 120]
        periods = self.da.drawdown_periods(curve)
        recovered = [p for p in periods if p.recovery_time is not None]
        assert len(recovered) >= 1

    def test_drawdown_periods_no_recovery(self):
        curve = [100, 110, 90, 85]
        periods = self.da.drawdown_periods(curve)
        unrecovered = [p for p in periods if p.recovery_time is None]
        assert len(unrecovered) >= 1

    def test_drawdown_periods_empty(self):
        assert self.da.drawdown_periods([]) == []
        assert self.da.drawdown_periods([100]) == []

    def test_underwater_chart_returns_html(self):
        curve = [100, 110, 95, 90, 100, 105]
        html = self.da.underwater_chart(curve)
        assert '<svg' in html
        assert 'Underwater Chart' in html

    def test_underwater_chart_insufficient(self):
        html = self.da.underwater_chart([100])
        assert 'Insufficient' in html

    def test_pain_index(self):
        curve = [100, 110, 100, 90, 100]
        pi = self.da.pain_index(curve)
        assert pi >= 0
        assert isinstance(pi, float)

    def test_pain_index_no_drawdown(self):
        curve = [100, 101, 102]
        assert self.da.pain_index(curve) == 0.0

    def test_ulcer_index(self):
        curve = [100, 110, 100, 90, 100]
        ui = self.da.ulcer_index(curve)
        assert ui >= 0
        assert isinstance(ui, float)

    def test_ulcer_index_no_drawdown(self):
        curve = [100, 101, 102]
        assert self.da.ulcer_index(curve) == 0.0

    def test_calmar_ratio_positive(self):
        returns = [0.01] * 252  # steady gains
        calmar = self.da.calmar_ratio(returns, -0.10)
        assert calmar > 0

    def test_calmar_ratio_zero_dd(self):
        assert self.da.calmar_ratio([0.01], 0) == 0.0

    def test_calmar_ratio_empty(self):
        assert self.da.calmar_ratio([], -0.1) == 0.0
