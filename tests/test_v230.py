"""
Tests for FinClaw v2.3.0 — Backtesting Deep Dive
Covers: RealisticBacktester, Benchmarks, StrategyComparator, TCA, HTML reports.
"""

import asyncio
import math
import pytest
from unittest.mock import MagicMock

# --- Helpers ---

def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_prices(start=100, n=300, trend=0.0005, vol=0.01):
    """Generate synthetic price series."""
    import random
    random.seed(42)
    prices = [start]
    for _ in range(n - 1):
        ret = trend + random.gauss(0, vol)
        prices.append(prices[-1] * (1 + ret))
    return prices


def make_bar_data(prices):
    """Convert price list to bar dicts."""
    return [
        {"price": p, "open": p * 0.999, "high": p * 1.005,
         "low": p * 0.995, "close": p, "volume": 1_000_000,
         "date": f"2024-{(i // 21) + 1:02d}-{(i % 21) + 1:02d}"}
        for i, p in enumerate(prices)
    ]


class SimpleStrategy:
    """Buy when 20-day SMA crosses above 50-day SMA, sell on cross below."""
    def generate_signal(self, prices):
        if len(prices) < 50:
            return MagicMock(signal="hold")
        sma20 = sum(prices[-20:]) / 20
        sma50 = sum(prices[-50:]) / 50
        # Also check previous bar for crossover
        if len(prices) >= 51:
            prev_sma20 = sum(prices[-21:-1]) / 20
            prev_sma50 = sum(prices[-51:-1]) / 50
            if sma20 > sma50 and prev_sma20 <= prev_sma50:
                return MagicMock(signal="buy")
            if sma20 < sma50 and prev_sma20 >= prev_sma50:
                return MagicMock(signal="sell")
        return MagicMock(signal="hold")


# ==================== RealisticBacktester ====================

class TestRealisticBacktester:

    def test_basic_run(self):
        from src.backtesting.realistic import RealisticBacktester, BacktestConfig
        config = BacktestConfig(initial_capital=100_000, slippage_bps=5, commission_rate=0.001)
        bt = RealisticBacktester(config)
        prices = make_prices(100, 200, trend=0.001)
        data = make_bar_data(prices)
        result = run_async(bt.run(SimpleStrategy(), data))
        assert result.equity_curve
        assert len(result.equity_curve) == len(data)
        assert result.total_return != 0 or result.total_trades == 0

    def test_config_defaults(self):
        from src.backtesting.realistic import BacktestConfig
        c = BacktestConfig()
        assert c.initial_capital == 100_000
        assert c.slippage_bps == 5.0
        assert c.commission_rate == 0.001
        assert c.margin_requirement == 1.0

    def test_too_few_bars_raises(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        with pytest.raises(ValueError, match="at least 30"):
            run_async(bt.run(SimpleStrategy(), [{"price": 100}] * 10))

    def test_equity_curve_starts_at_capital(self):
        from src.backtesting.realistic import RealisticBacktester, BacktestConfig
        config = BacktestConfig(initial_capital=50_000)
        bt = RealisticBacktester(config)
        data = make_bar_data(make_prices(100, 50, trend=0))
        result = run_async(bt.run(SimpleStrategy(), data))
        assert abs(result.equity_curve[0] - 50_000) < 1

    def test_commission_charged(self):
        from src.backtesting.realistic import RealisticBacktester, BacktestConfig
        config = BacktestConfig(commission_rate=0.01)  # 1% — very high
        bt = RealisticBacktester(config)
        data = make_bar_data(make_prices(100, 200, trend=0.001))
        result = run_async(bt.run(SimpleStrategy(), data))
        if result.total_trades > 0:
            assert result.total_commission > 0

    def test_callable_strategy(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        call_count = [0]
        def strat(prices):
            call_count[0] += 1
            if len(prices) > 50:
                sma = sum(prices[-20:]) / 20
                return "buy" if prices[-1] > sma and call_count[0] % 40 == 0 else "hold"
            return "hold"
        data = make_bar_data(make_prices(100, 100))
        result = run_async(bt.run(strat, data))
        assert result.equity_curve

    def test_summary_string(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        data = make_bar_data(make_prices(100, 100))
        result = run_async(bt.run(SimpleStrategy(), data))
        result.strategy_name = "TestStrat"
        s = result.summary()
        assert "TestStrat" in s
        assert "REALISTIC BACKTEST" in s

    def test_with_benchmark(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        prices = make_prices(100, 200, trend=0.001)
        data = make_bar_data(prices)
        bench = make_prices(100, 200, trend=0.0005)
        result = run_async(bt.run(SimpleStrategy(), data, benchmark=bench))
        assert result.benchmark_return is not None

    def test_drawdown_curve(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        data = make_bar_data(make_prices(100, 100))
        result = run_async(bt.run(SimpleStrategy(), data))
        assert len(result.drawdown_curve) == len(result.equity_curve)
        assert all(dd <= 0 for dd in result.drawdown_curve)

    def test_daily_returns_length(self):
        from src.backtesting.realistic import RealisticBacktester
        bt = RealisticBacktester()
        data = make_bar_data(make_prices(100, 100))
        result = run_async(bt.run(SimpleStrategy(), data))
        assert len(result.daily_returns) == len(result.equity_curve) - 1


# ==================== SlippageModel ====================

class TestSlippageModel:

    def test_buy_slippage_increases_price(self):
        from src.backtesting.realistic import SlippageModel, OrderSide
        sm = SlippageModel(bps=10)
        slipped = sm.apply(100.0, OrderSide.BUY)
        assert slipped > 100.0

    def test_sell_slippage_decreases_price(self):
        from src.backtesting.realistic import SlippageModel, OrderSide
        sm = SlippageModel(bps=10)
        slipped = sm.apply(100.0, OrderSide.SELL)
        assert slipped < 100.0

    def test_zero_slippage(self):
        from src.backtesting.realistic import SlippageModel, OrderSide
        sm = SlippageModel(bps=0)
        assert sm.apply(100, OrderSide.BUY) == 100

    def test_cost_calculation(self):
        from src.backtesting.realistic import SlippageModel
        sm = SlippageModel(bps=10)
        cost = sm.cost(100, 100)
        assert abs(cost - 10.0) < 0.01  # 10bps of $10,000


# ==================== CommissionModel ====================

class TestCommissionModel:

    def test_basic_commission(self):
        from src.backtesting.realistic import CommissionModel
        cm = CommissionModel(rate=0.001)
        assert abs(cm.calculate(100, 100) - 10.0) < 0.01

    def test_minimum_commission(self):
        from src.backtesting.realistic import CommissionModel
        cm = CommissionModel(rate=0.001, minimum=5.0)
        assert cm.calculate(1.0, 1) == 5.0  # min kicks in


# ==================== MarketImpactModel ====================

class TestMarketImpactModel:

    def test_small_order_small_impact(self):
        from src.backtesting.realistic import MarketImpactModel
        mi = MarketImpactModel(coeff=0.1)
        bps = mi.impact_bps(100, 1_000_000)
        assert bps < 50  # small order, small impact

    def test_large_order_larger_impact(self):
        from src.backtesting.realistic import MarketImpactModel
        mi = MarketImpactModel(coeff=0.1)
        small = mi.impact_bps(100, 1_000_000)
        large = mi.impact_bps(100_000, 1_000_000)
        assert large > small


# ==================== SimpleOrderBook ====================

class TestSimpleOrderBook:

    def test_market_order_fills_at_open(self):
        from src.backtesting.realistic import (
            SimpleOrderBook, OrderSide, OrderType, BacktestConfig,
            SlippageModel, CommissionModel, MarketImpactModel, FillStatus,
        )
        book = SimpleOrderBook()
        book.submit(OrderSide.BUY, OrderType.MARKET, 100, bar=0)
        filled = book.process_bar(
            1, 100, 105, 95, 102, 1_000_000,
            BacktestConfig(slippage_bps=0, commission_rate=0, impact_coeff=0),
            SlippageModel(0), CommissionModel(0), MarketImpactModel(0),
        )
        assert len(filled) == 1
        assert filled[0].filled_price == 100  # opens at 100
        assert filled[0].status == FillStatus.FILLED

    def test_limit_order_fills_when_price_touches(self):
        from src.backtesting.realistic import (
            SimpleOrderBook, OrderSide, OrderType, BacktestConfig,
            SlippageModel, CommissionModel, MarketImpactModel,
        )
        book = SimpleOrderBook()
        book.submit(OrderSide.BUY, OrderType.LIMIT, 100, limit_price=95, bar=0)
        # Bar where low touches 95
        filled = book.process_bar(
            0, 100, 105, 94, 102, 1_000_000,
            BacktestConfig(slippage_bps=0, commission_rate=0, impact_coeff=0, order_ttl_bars=5),
            SlippageModel(0), CommissionModel(0), MarketImpactModel(0),
        )
        assert len(filled) == 1
        assert filled[0].filled_price <= 95

    def test_limit_order_not_filled_when_price_away(self):
        from src.backtesting.realistic import (
            SimpleOrderBook, OrderSide, OrderType, BacktestConfig,
            SlippageModel, CommissionModel, MarketImpactModel,
        )
        book = SimpleOrderBook()
        book.submit(OrderSide.BUY, OrderType.LIMIT, 100, limit_price=90, bar=0)
        filled = book.process_bar(
            0, 100, 105, 95, 102, 1_000_000,
            BacktestConfig(slippage_bps=0, commission_rate=0, impact_coeff=0, order_ttl_bars=5),
            SlippageModel(0), CommissionModel(0), MarketImpactModel(0),
        )
        assert len(filled) == 0

    def test_stop_order(self):
        from src.backtesting.realistic import (
            SimpleOrderBook, OrderSide, OrderType, BacktestConfig,
            SlippageModel, CommissionModel, MarketImpactModel,
        )
        book = SimpleOrderBook()
        book.submit(OrderSide.SELL, OrderType.STOP, 100, stop_price=95, bar=0)
        filled = book.process_bar(
            0, 100, 105, 94, 96, 1_000_000,
            BacktestConfig(slippage_bps=0, commission_rate=0, impact_coeff=0, order_ttl_bars=5),
            SlippageModel(0), CommissionModel(0), MarketImpactModel(0),
        )
        assert len(filled) == 1

    def test_cancel_all(self):
        from src.backtesting.realistic import SimpleOrderBook, OrderSide, OrderType
        book = SimpleOrderBook()
        book.submit(OrderSide.BUY, OrderType.MARKET, 100)
        book.submit(OrderSide.BUY, OrderType.LIMIT, 50, limit_price=90)
        assert book.pending_count == 2
        book.cancel_all()
        assert book.pending_count == 0


# ==================== Benchmarks ====================

class TestBenchmarks:

    def test_buy_and_hold(self):
        from src.backtesting.benchmarks import BuyAndHold
        bh = BuyAndHold("SPY")
        prices = make_prices(100, 252, trend=0.0004)
        result = bh.run({"SPY": prices})
        assert result.total_return > 0
        assert result.sharpe_ratio != 0
        assert len(result.equity_curve) == len(prices)

    def test_buy_and_hold_missing_symbol(self):
        from src.backtesting.benchmarks import BuyAndHold
        bh = BuyAndHold("XYZ")
        result = bh.run({"SPY": [100, 110]})
        assert result.total_return == 0

    def test_equal_weight(self):
        from src.backtesting.benchmarks import EqualWeight
        ew = EqualWeight(["A", "B"])
        data = {
            "A": make_prices(100, 100, trend=0.001),
            "B": make_prices(50, 100, trend=0.0005),
        }
        result = ew.run(data)
        assert result.total_return != 0
        assert len(result.equity_curve) > 0

    def test_classic_60_40(self):
        from src.backtesting.benchmarks import ClassicPortfolio
        cp = ClassicPortfolio(stocks_pct=0.6, bonds_pct=0.4)
        data = {
            "SPY": make_prices(100, 100, trend=0.001),
            "TLT": make_prices(50, 100, trend=0.0002),
        }
        result = cp.run(data)
        assert result.total_return != 0

    def test_risk_parity(self):
        from src.backtesting.benchmarks import RiskParityBenchmark
        rp = RiskParityBenchmark(symbols=["A", "B"], lookback=30)
        data = {
            "A": make_prices(100, 200, trend=0.001, vol=0.02),
            "B": make_prices(50, 200, trend=0.0005, vol=0.005),
        }
        result = rp.run(data)
        assert len(result.equity_curve) > 30

    def test_run_all_benchmarks(self):
        from src.backtesting.benchmarks import run_all_benchmarks, BuyAndHold
        data = {"SPY": make_prices(100, 300, trend=0.0003)}
        results = run_all_benchmarks(data, custom={"custom_bh": BuyAndHold("SPY")})
        assert "buy_and_hold_spy" in results
        assert "custom_bh" in results

    def test_benchmark_result_summary_row(self):
        from src.backtesting.benchmarks import BenchmarkResult
        br = BenchmarkResult(name="Test", total_return=0.15, cagr=0.12,
                             sharpe_ratio=1.5, sortino_ratio=2.0,
                             max_drawdown=-0.10, volatility=0.15)
        row = br.summary_row()
        assert row["Name"] == "Test"
        assert "15" in row["Return"]


# ==================== StrategyComparator ====================

class TestStrategyComparator:

    def test_compare_two_strategies(self):
        from src.backtesting.compare import StrategyComparator
        comp = StrategyComparator()
        r1 = MagicMock(total_return=0.20, annualized_return=0.18, cagr=0.18,
                       sharpe_ratio=1.5, sortino_ratio=2.0, max_drawdown=-0.10,
                       volatility=0.15, calmar_ratio=1.8, win_rate=0.55,
                       profit_factor=1.8, total_trades=50, total_costs=100,
                       equity_curve=[], daily_returns=[0.001] * 100)
        r2 = MagicMock(total_return=0.10, annualized_return=0.09, cagr=0.09,
                       sharpe_ratio=0.8, sortino_ratio=1.0, max_drawdown=-0.20,
                       volatility=0.20, calmar_ratio=0.5, win_rate=0.45,
                       profit_factor=1.1, total_trades=30, total_costs=50,
                       equity_curve=[], daily_returns=[0.0005] * 100)
        comp.add("Strat A", r1)
        comp.add("Strat B", r2)
        result = comp.compare()
        assert result.best_overall == "Strat A"
        assert "Sharpe" in result.rankings
        assert result.rankings["Sharpe"][0] == "Strat A"

    def test_compare_table_output(self):
        from src.backtesting.compare import StrategyComparator
        comp = StrategyComparator()
        r1 = MagicMock(total_return=0.20, cagr=0.18, sharpe_ratio=1.5,
                       sortino_ratio=2.0, max_drawdown=-0.10, volatility=0.15,
                       calmar_ratio=1.8, win_rate=0.55, profit_factor=1.8,
                       total_trades=50, total_costs=100,
                       equity_curve=[], daily_returns=[])
        comp.add("Strat", r1)
        result = comp.compare()
        table = result.table()
        assert "Strat" in table

    def test_empty_comparator(self):
        from src.backtesting.compare import StrategyComparator
        comp = StrategyComparator()
        result = comp.compare()
        assert result.strategies == []

    def test_correlation_matrix(self):
        from src.backtesting.compare import StrategyComparator
        comp = StrategyComparator()
        rets_a = [0.01 * (i % 3 - 1) for i in range(100)]
        rets_b = [0.01 * ((i + 1) % 3 - 1) for i in range(100)]
        r1 = MagicMock(total_return=0.1, cagr=0.1, sharpe_ratio=1.0,
                       sortino_ratio=1.0, max_drawdown=-0.05, volatility=0.1,
                       calmar_ratio=2, win_rate=0.5, profit_factor=1.5,
                       total_trades=20, total_costs=10,
                       equity_curve=[], daily_returns=rets_a)
        r2 = MagicMock(total_return=0.08, cagr=0.08, sharpe_ratio=0.9,
                       sortino_ratio=0.9, max_drawdown=-0.06, volatility=0.12,
                       calmar_ratio=1.5, win_rate=0.48, profit_factor=1.3,
                       total_trades=18, total_costs=8,
                       equity_curve=[], daily_returns=rets_b)
        comp.add("A", r1)
        comp.add("B", r2)
        result = comp.compare()
        assert result.correlation_matrix is not None
        assert "A" in result.correlation_matrix
        assert abs(result.correlation_matrix["A"]["A"] - 1.0) < 0.01

    def test_reset(self):
        from src.backtesting.compare import StrategyComparator
        comp = StrategyComparator()
        comp.add("X", MagicMock(total_return=0, cagr=0, sharpe_ratio=0,
                                sortino_ratio=0, max_drawdown=0, volatility=0,
                                calmar_ratio=0, win_rate=0, profit_factor=0,
                                total_trades=0, total_costs=0,
                                equity_curve=[], daily_returns=[]))
        comp.reset()
        assert comp.compare().strategies == []


# ==================== TCA ====================

class TestTCA:

    def test_basic_tca(self):
        from src.analytics.tca import TCA, TradeFill
        tca = TCA()
        fills = [
            TradeFill(ticker="AAPL", side="buy", quantity=100,
                      decision_price=150.0, fill_price=150.10, commission=1.0),
            TradeFill(ticker="AAPL", side="sell", quantity=100,
                      decision_price=155.0, fill_price=154.90, commission=1.0),
        ]
        report = tca.analyze(fills, gross_return=490)
        assert report.n_trades == 2
        assert report.commission_cost == 2.0
        assert report.slippage_cost > 0
        assert report.total_cost_bps > 0

    def test_empty_trades(self):
        from src.analytics.tca import TCA
        tca = TCA()
        report = tca.analyze([])
        assert report.n_trades == 0
        assert report.total_cost_bps == 0

    def test_cost_by_ticker(self):
        from src.analytics.tca import TCA, TradeFill
        tca = TCA()
        fills = [
            TradeFill(ticker="AAPL", side="buy", quantity=100,
                      decision_price=150, fill_price=150.05, commission=1),
            TradeFill(ticker="MSFT", side="buy", quantity=50,
                      decision_price=300, fill_price=300.10, commission=2),
        ]
        report = tca.analyze(fills)
        assert "AAPL" in report.cost_by_ticker
        assert "MSFT" in report.cost_by_ticker

    def test_tca_summary(self):
        from src.analytics.tca import TCA, TradeFill
        tca = TCA()
        fills = [
            TradeFill(ticker="X", side="buy", quantity=10,
                      decision_price=100, fill_price=100.5, commission=0.5),
        ]
        report = tca.analyze(fills)
        s = report.summary()
        assert "Transaction Cost Analysis" in s

    def test_from_backtest_trades(self):
        from src.analytics.tca import TCA
        from src.backtesting.realistic import TradeRecord
        tca = TCA()
        trades = [
            TradeRecord(entry_bar=10, exit_bar=20, entry_price=100,
                        exit_price=110, quantity=50, side="long",
                        pnl=500, pnl_pct=0.10, commission=5,
                        slippage_cost=2, impact_cost=1, holding_bars=10),
        ]
        report = tca.from_backtest_trades(trades)
        assert report.n_trades == 1


# ==================== HTML Report ====================

class TestHTMLReport:

    def test_generate_basic_report(self):
        from src.reports.html_report import generate_html_report
        data = {
            "total_return": 0.15, "annualized_return": 0.12,
            "sharpe_ratio": 1.5, "sortino_ratio": 2.0,
            "max_drawdown": -0.10, "win_rate": 0.55,
            "profit_factor": 1.8, "num_trades": 50,
            "avg_trade_return": 0.003, "avg_win": 0.02,
            "avg_loss": -0.01, "equity_curve": list(range(100, 200)),
        }
        html = generate_html_report(data, title="Test Report")
        assert "Test Report" in html
        assert "FinClaw" in html
        assert "<!DOCTYPE html>" in html

    def test_report_with_tca(self):
        from src.reports.html_report import generate_html_report
        data = {
            "total_return": 0.1, "annualized_return": 0.08,
            "sharpe_ratio": 1.0, "sortino_ratio": 1.2,
            "max_drawdown": -0.05, "win_rate": 0.5,
            "profit_factor": 1.5, "num_trades": 20,
            "avg_trade_return": 0.005, "avg_win": 0.02,
            "avg_loss": -0.015,
            "tca": {
                "total_cost_bps": 15.5, "commission_cost": 100,
                "slippage_cost": 50, "market_impact": 20,
                "opportunity_cost": 10, "cost_as_pct_of_gross_return": 0.05,
            },
        }
        html = generate_html_report(data)
        assert "Transaction Cost" in html

    def test_report_with_comparison(self):
        from src.reports.html_report import generate_html_report
        data = {
            "total_return": 0.1, "annualized_return": 0.08,
            "sharpe_ratio": 1.0, "sortino_ratio": 1.2,
            "max_drawdown": -0.05, "win_rate": 0.5,
            "profit_factor": 1.5, "num_trades": 20,
            "avg_trade_return": 0.005, "avg_win": 0.02,
            "avg_loss": -0.015,
            "comparison": {
                "strategies": [
                    {"name": "Momentum", "total_return": 0.15, "cagr": 0.12,
                     "sharpe_ratio": 1.5, "sortino_ratio": 2.0,
                     "max_drawdown": -0.1, "win_rate": 0.55, "profit_factor": 1.8},
                    {"name": "SPY B&H", "total_return": 0.10, "cagr": 0.09,
                     "sharpe_ratio": 0.8, "sortino_ratio": 1.0,
                     "max_drawdown": -0.15, "win_rate": 0, "profit_factor": 0},
                ],
                "best_overall": "Momentum",
            },
        }
        html = generate_html_report(data)
        assert "Strategy Comparison" in html
        assert "Momentum" in html


# ==================== Integration ====================

class TestIntegration:

    def test_backtest_then_tca(self):
        """Run realistic backtest then feed trades to TCA."""
        from src.backtesting.realistic import RealisticBacktester, BacktestConfig
        from src.analytics.tca import TCA

        config = BacktestConfig(slippage_bps=10, commission_rate=0.002)
        bt = RealisticBacktester(config)
        data = make_bar_data(make_prices(100, 200, trend=0.001))
        result = run_async(bt.run(SimpleStrategy(), data))

        tca = TCA()
        report = tca.from_backtest_trades(result.trades)
        assert report.n_trades == result.total_trades

    def test_backtest_then_compare(self):
        """Run two backtests and compare."""
        from src.backtesting.realistic import RealisticBacktester, BacktestConfig
        from src.backtesting.compare import StrategyComparator

        data = make_bar_data(make_prices(100, 200, trend=0.001))

        bt1 = RealisticBacktester(BacktestConfig(slippage_bps=5))
        r1 = run_async(bt1.run(SimpleStrategy(), data))
        r1.strategy_name = "SMA Cross"

        bt2 = RealisticBacktester(BacktestConfig(slippage_bps=20))
        r2 = run_async(bt2.run(SimpleStrategy(), data))
        r2.strategy_name = "SMA Cross (High Slip)"

        comp = StrategyComparator()
        comp.add("SMA Cross", r1)
        comp.add("High Slip", r2)
        result = comp.compare()
        assert len(result.strategies) == 2
        assert result.best_overall in ("SMA Cross", "High Slip")

    def test_benchmarks_and_compare(self):
        """Run benchmarks then compare with strategy."""
        from src.backtesting.benchmarks import BuyAndHold
        from src.backtesting.compare import StrategyComparator

        prices = make_prices(100, 252, trend=0.0004)
        bh = BuyAndHold("SPY")
        bh_result = bh.run({"SPY": prices})

        comp = StrategyComparator()
        comp.add("SPY B&H", bh_result)
        # Add a fake strategy result
        from unittest.mock import MagicMock
        strat = MagicMock(total_return=0.25, cagr=0.25, sharpe_ratio=2.0,
                          sortino_ratio=3.0, max_drawdown=-0.05, volatility=0.10,
                          calmar_ratio=5.0, win_rate=0.60, profit_factor=2.5,
                          total_trades=40, total_costs=200,
                          equity_curve=[], daily_returns=[])
        comp.add("Alpha Strat", strat)
        result = comp.compare()
        assert len(result.strategies) == 2
        assert result.best_overall in ("Alpha Strat", "SPY B&H")
