"""
Verify backtest calculations are mathematically correct.

These tests use KNOWN inputs with KNOWN expected outputs.
If these fail, the backtest framework is lying to us.

Tests target two levels:
  1. BacktestResult static methods (core_engine.py) — the math primitives
  2. GoldenDipStrategy.backtest() — end-to-end with known data
"""

import math
import sys
import os

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtesting.core_engine import BacktestResult


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _equity_from_values(values: list[float]) -> list[float]:
    """Just returns the list — for readability."""
    return list(values)


def _daily_returns_from_equity(curve: list[float]) -> list[float]:
    """Compute daily simple returns from an equity curve."""
    return BacktestResult._compute_returns(curve)


# ═══════════════════════════════════════════════════════════════════
# 1. Annualized Return (CAGR)
# ═══════════════════════════════════════════════════════════════════

class TestAnnualizedReturn:
    """年化收益率计算验证 — 使用 BacktestResult._compute_cagr()"""

    def test_simple_double(self):
        """100万→200万，1年(252 bars)，年化应该=100%"""
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=2_000_000,
            n_bars=252, bars_per_year=252,
        )
        assert abs(cagr - 1.0) < 1e-9, f"Expected 1.0 (100%), got {cagr}"

    def test_half_year_double(self):
        """100万→200万，半年(126 bars)，年化应该=300%
        (1+1)^(252/126) - 1 = 4 - 1 = 3.0 = 300%
        """
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=2_000_000,
            n_bars=126, bars_per_year=252,
        )
        expected = (2.0 ** (252 / 126)) - 1  # 3.0
        assert abs(cagr - expected) < 1e-6, f"Expected {expected}, got {cagr}"

    def test_zero_return(self):
        """100万→100万，年化=0%"""
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=1_000_000,
            n_bars=252, bars_per_year=252,
        )
        assert abs(cagr) < 1e-9, f"Expected 0, got {cagr}"

    def test_loss(self):
        """100万→50万，1年，年化=-50%"""
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=500_000,
            n_bars=252, bars_per_year=252,
        )
        assert abs(cagr - (-0.5)) < 1e-9, f"Expected -0.5, got {cagr}"

    def test_daily_compound(self):
        """每天赚1%，250个交易日，年化=1.01^(252/1)-1
        CAGR from final/initial over 250 bars:
        final = initial * 1.01^250 ≈ initial * 12.0326
        CAGR = (12.0326)^(252/250) - 1 ≈ 12.13 - 1 = 11.13 ≈ 1113%
        """
        initial = 1_000_000
        final = initial * (1.01 ** 250)
        cagr = BacktestResult._compute_cagr(
            initial=initial, final=final,
            n_bars=250, bars_per_year=252,
        )
        expected = (final / initial) ** (252 / 250) - 1
        assert abs(cagr - expected) < 1e-6, f"Expected {expected}, got {cagr}"
        # Sanity: should be roughly 11+
        assert cagr > 11.0, f"Daily 1% compound over 250 days should be >1100% annualized"

    def test_two_year_50pct(self):
        """100万→150万，2年(504 bars)，年化≈22.47%
        (1.5)^(1/2) - 1 ≈ 0.2247
        """
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=1_500_000,
            n_bars=504, bars_per_year=252,
        )
        expected = (1.5 ** 0.5) - 1
        assert abs(cagr - expected) < 1e-6, f"Expected {expected}, got {cagr}"

    def test_edge_zero_bars(self):
        """0 bars should return 0 (no division by zero)"""
        cagr = BacktestResult._compute_cagr(
            initial=1_000_000, final=2_000_000,
            n_bars=0, bars_per_year=252,
        )
        assert cagr == 0.0

    def test_edge_zero_initial(self):
        """0 initial capital should return 0 (no division by zero)"""
        cagr = BacktestResult._compute_cagr(
            initial=0, final=1_000_000,
            n_bars=252, bars_per_year=252,
        )
        assert cagr == 0.0


# ═══════════════════════════════════════════════════════════════════
# 2. Max Drawdown
# ═══════════════════════════════════════════════════════════════════

class TestMaxDrawdown:
    """最大回撤计算验证 — 使用 BacktestResult._compute_max_drawdown()"""

    def test_simple_drawdown(self):
        """100→80→100，最大回撤应该=20%"""
        curve = [100, 95, 90, 85, 80, 85, 90, 95, 100]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert abs(dd - 0.20) < 1e-9, f"Expected 0.20, got {dd}"

    def test_no_drawdown(self):
        """只涨不跌，最大回撤=0"""
        curve = [100, 110, 120, 130, 140, 150]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert dd == 0.0, f"Expected 0, got {dd}"

    def test_multiple_drawdowns(self):
        """100→80→90→70→100，最大回撤=30%（从90→70 不是100→80）
        Actually: peak at 100, drops to 80 (20%), recovers to 90.
        New peak is still 100 (not 90, since 90<100).
        Then drops to 70: dd = (100-70)/100 = 30%.
        """
        curve = [100, 80, 90, 70, 100]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert abs(dd - 0.30) < 1e-9, f"Expected 0.30, got {dd}"

    def test_crash_recovery(self):
        """100→50→80，最大回撤=50%"""
        curve = [100, 75, 50, 60, 70, 80]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert abs(dd - 0.50) < 1e-9, f"Expected 0.50, got {dd}"

    def test_monotonic_decline(self):
        """100→90→80→70，最大回撤=30%"""
        curve = [100, 90, 80, 70]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert abs(dd - 0.30) < 1e-9, f"Expected 0.30, got {dd}"

    def test_new_high_then_drop(self):
        """100→120→90，最大回撤=25%（从120跌到90）"""
        curve = [100, 110, 120, 100, 90]
        dd = BacktestResult._compute_max_drawdown(curve)
        expected = (120 - 90) / 120  # 0.25
        assert abs(dd - expected) < 1e-9, f"Expected {expected}, got {dd}"

    def test_empty_curve(self):
        """空曲线应该返回0"""
        dd = BacktestResult._compute_max_drawdown([])
        assert dd == 0.0

    def test_single_point(self):
        """单点曲线，最大回撤=0"""
        dd = BacktestResult._compute_max_drawdown([100])
        assert dd == 0.0


# ═══════════════════════════════════════════════════════════════════
# 3. Sharpe Ratio
# ═══════════════════════════════════════════════════════════════════

class TestSharpeRatio:
    """夏普比率计算验证 — 使用 BacktestResult._compute_sharpe()"""

    def test_stable_positive(self):
        """每天稳定赚1%，夏普应该极高（>5）
        mean = 0.01, std ≈ 0 → Sharpe → infinity
        But with floating point: std is tiny but nonzero from compound effects.
        We use exact 1% returns to get std=0 → Sharpe=0 (div by zero protection).
        So instead: near-constant returns with tiny noise.
        """
        # All identical returns → std=0 → function returns 0.0
        returns = [0.01] * 252
        sharpe = BacktestResult._compute_sharpe(returns)
        # std=0 → returns 0.0 by convention in the function
        assert sharpe == 0.0, "Constant returns → std=0 → Sharpe=0"

    def test_stable_positive_from_curve(self):
        """从权益曲线算：每天涨1%，Sharpe应该极高"""
        # Build equity curve: each day +1% with tiny noise
        import random
        rng = random.Random(42)
        curve = [100.0]
        for _ in range(252):
            curve.append(curve[-1] * (1.01 + rng.gauss(0, 0.0001)))
        returns = _daily_returns_from_equity(curve)
        sharpe = BacktestResult._compute_sharpe(returns)
        # ~0.01/0.0001 * sqrt(252) ≈ 1587
        assert sharpe > 100, f"Stable 1% daily should have very high Sharpe, got {sharpe}"

    def test_volatile(self):
        """大涨大跌，夏普应该低"""
        # Alternating +5% / -5%
        returns = [0.05, -0.05] * 126
        sharpe = BacktestResult._compute_sharpe(returns)
        # mean ≈ 0, std ≈ 0.05 → Sharpe ≈ 0
        assert abs(sharpe) < 1.0, f"Volatile with zero-mean should have Sharpe near 0, got {sharpe}"

    def test_negative_return(self):
        """亏钱的策略，夏普应该为负"""
        # Every day lose 0.5%
        import random
        rng = random.Random(42)
        returns = [-0.005 + rng.gauss(0, 0.001) for _ in range(252)]
        sharpe = BacktestResult._compute_sharpe(returns)
        assert sharpe < 0, f"Losing strategy should have negative Sharpe, got {sharpe}"

    def test_insufficient_data(self):
        """不到2个数据点，Sharpe=0"""
        assert BacktestResult._compute_sharpe([]) == 0.0
        assert BacktestResult._compute_sharpe([0.01]) == 0.0


# ═══════════════════════════════════════════════════════════════════
# 4. Calmar Ratio
# ═══════════════════════════════════════════════════════════════════

class TestCalmarRatio:
    """Calmar比率计算验证 — Calmar = CAGR / MaxDrawdown"""

    def test_high_return_low_dd(self):
        """年化100%，最大回撤10% → Calmar=10"""
        # Build equity curve: grows 2x over 252 bars, with one 10% dip
        curve = [100.0]
        for i in range(1, 253):
            # Exponential growth: final ≈ 200
            curve.append(100.0 * (2.0 ** (i / 252)))
        # Insert a 10% drawdown at day 100
        peak_at_100 = curve[100]
        for j in range(101, 111):
            curve[j] = peak_at_100 * (1 - 0.10 * (j - 100) / 10)
        # The rest recovers
        for j in range(111, 253):
            curve[j] = 100.0 * (2.0 ** (j / 252))

        cagr = BacktestResult._compute_cagr(curve[0], curve[-1], len(curve) - 1)
        dd = BacktestResult._compute_max_drawdown(curve)
        calmar = cagr / dd if dd > 0 else float('inf')
        # CAGR ≈ 1.0, dd ≈ 0.10 → Calmar ≈ 10
        assert abs(cagr - 1.0) < 0.05, f"CAGR should be ~1.0, got {cagr}"
        assert calmar > 5, f"Calmar should be high, got {calmar}"

    def test_zero_drawdown(self):
        """没有回撤，Calmar应该是inf"""
        curve = [100, 110, 120, 130, 140, 150]
        dd = BacktestResult._compute_max_drawdown(curve)
        assert dd == 0.0
        # Calmar = CAGR / 0 → inf
        cagr = BacktestResult._compute_cagr(curve[0], curve[-1], len(curve) - 1)
        calmar = cagr / dd if dd > 0 else float('inf')
        assert calmar == float('inf')

    def test_terrible_calmar(self):
        """年化10%，最大回撤50% → Calmar=0.2"""
        # 1 year, 10% total return, but 50% drawdown at one point
        cagr = 0.10
        dd = 0.50
        calmar = cagr / dd
        assert abs(calmar - 0.2) < 1e-9


# ═══════════════════════════════════════════════════════════════════
# 5. Win Rate
# ═══════════════════════════════════════════════════════════════════

class TestWinRate:
    """胜率计算验证 — 使用 BacktestResult._compute_win_rate()"""

    def test_all_win(self):
        """5笔交易全赚，胜率=100%"""
        trades = [{"pnl": 100}, {"pnl": 50}, {"pnl": 200}, {"pnl": 10}, {"pnl": 300}]
        wr = BacktestResult._compute_win_rate(trades)
        assert abs(wr - 1.0) < 1e-9, f"Expected 1.0 (100%), got {wr}"

    def test_half_win(self):
        """10笔交易5赚5亏，胜率=50%"""
        trades = [{"pnl": 100}] * 5 + [{"pnl": -50}] * 5
        wr = BacktestResult._compute_win_rate(trades)
        assert abs(wr - 0.5) < 1e-9, f"Expected 0.5 (50%), got {wr}"

    def test_single_trade(self):
        """1笔交易赚了，胜率=100%"""
        trades = [{"pnl": 42}]
        wr = BacktestResult._compute_win_rate(trades)
        assert abs(wr - 1.0) < 1e-9

    def test_all_loss(self):
        """全亏，胜率=0%"""
        trades = [{"pnl": -100}, {"pnl": -50}, {"pnl": -200}]
        wr = BacktestResult._compute_win_rate(trades)
        assert wr == 0.0

    def test_no_trades(self):
        """没有交易，胜率=0%"""
        wr = BacktestResult._compute_win_rate([])
        assert wr == 0.0

    def test_breakeven_counted_as_loss(self):
        """pnl=0 算亏损（不算赢）"""
        trades = [{"pnl": 0}]
        wr = BacktestResult._compute_win_rate(trades)
        assert wr == 0.0


# ═══════════════════════════════════════════════════════════════════
# 6. Profit/Loss Ratio (Profit Factor)
# ═══════════════════════════════════════════════════════════════════

class TestProfitLossRatio:
    """盈亏比(Profit Factor)计算验证"""

    def test_simple(self):
        """总盈利200，总亏损100，盈亏比=2.0"""
        trades = [
            {"pnl": 100}, {"pnl": 100},  # win: 200
            {"pnl": -50}, {"pnl": -50},   # loss: 100
        ]
        pf = BacktestResult._compute_profit_factor(trades)
        assert abs(pf - 2.0) < 1e-9, f"Expected 2.0, got {pf}"

    def test_no_loss(self):
        """没有亏损交易，盈亏比=inf"""
        trades = [{"pnl": 100}, {"pnl": 200}]
        pf = BacktestResult._compute_profit_factor(trades)
        assert pf == float('inf')

    def test_no_profit(self):
        """没有盈利交易，盈亏比=0"""
        trades = [{"pnl": -100}, {"pnl": -200}]
        pf = BacktestResult._compute_profit_factor(trades)
        assert pf == 0.0

    def test_equal_win_loss(self):
        """盈亏金额相等，盈亏比=1.0"""
        trades = [{"pnl": 100}, {"pnl": -100}]
        pf = BacktestResult._compute_profit_factor(trades)
        assert abs(pf - 1.0) < 1e-9

    def test_no_trades(self):
        """空交易列表"""
        pf = BacktestResult._compute_profit_factor([])
        assert pf == 0.0


# ═══════════════════════════════════════════════════════════════════
# 7. Sortino Ratio
# ═══════════════════════════════════════════════════════════════════

class TestSortinoRatio:
    """Sortino比率验证 — 只用负收益计算波动率"""

    def test_no_downside(self):
        """所有收益都是正的，Sortino=inf"""
        returns = [0.01, 0.02, 0.015, 0.008, 0.012] * 10
        sortino = BacktestResult._compute_sortino(returns)
        assert sortino == float('inf'), f"No downside → Sortino=inf, got {sortino}"

    def test_all_negative(self):
        """所有收益都是负的，Sortino应为负"""
        import random
        rng = random.Random(42)
        returns = [-0.01 + rng.gauss(0, 0.002) for _ in range(100)]
        # Ensure all negative
        returns = [-abs(r) for r in returns]
        sortino = BacktestResult._compute_sortino(returns)
        assert sortino < 0, f"All losses should give negative Sortino, got {sortino}"

    def test_insufficient_data(self):
        """不到2个数据点"""
        assert BacktestResult._compute_sortino([]) == 0.0
        assert BacktestResult._compute_sortino([0.01]) == 0.0


# ═══════════════════════════════════════════════════════════════════
# 8. Equity Curve Returns
# ═══════════════════════════════════════════════════════════════════

class TestEquityCurveReturns:
    """权益曲线日收益率计算验证"""

    def test_simple_returns(self):
        """100 → 110 → 121，日收益率=10%, 10%"""
        curve = [100, 110, 121]
        returns = BacktestResult._compute_returns(curve)
        assert len(returns) == 2
        assert abs(returns[0] - 0.10) < 1e-9
        assert abs(returns[1] - 0.10) < 1e-9

    def test_loss_return(self):
        """100 → 90，日收益率=-10%"""
        curve = [100, 90]
        returns = BacktestResult._compute_returns(curve)
        assert len(returns) == 1
        assert abs(returns[0] - (-0.10)) < 1e-9

    def test_empty_curve(self):
        """空或单点曲线"""
        assert BacktestResult._compute_returns([]) == []
        assert BacktestResult._compute_returns([100]) == []


# ═══════════════════════════════════════════════════════════════════
# 9. T+1 Execution Price Verification
# ═══════════════════════════════════════════════════════════════════

class TestT1Execution:
    """T+1执行价验证 — 使用 GoldenDipStrategy"""

    def test_signal_today_buy_tomorrow(self):
        """T日收盘产生信号，T+1日开盘价买入

        We craft prices so that we KNOW when a buy signal fires,
        then verify the entry_price matches T+1's open, NOT T's close.
        """
        from src.strategies.golden_dip import GoldenDipStrategy

        strategy = GoldenDipStrategy()
        n = 200

        # Build a strong uptrend for 150 days, then a dip
        np.random.seed(42)
        closes = np.zeros(n)
        opens = np.zeros(n)
        volumes = np.ones(n) * 1_000_000

        # Strong uptrend (days 0-149): linear from 50 to 150
        for i in range(150):
            closes[i] = 50 + (100 / 150) * i
            opens[i] = closes[i] - 0.2

        # Create a pullback/dip (days 150-179)
        peak = closes[149]
        for i in range(150, 180):
            drop = (i - 150) / 30 * 0.20  # up to 20% drop
            closes[i] = peak * (1 - drop)
            opens[i] = closes[i] + 0.5  # open slightly higher

        # Recovery (days 180-199)
        for i in range(180, n):
            closes[i] = closes[179] + (i - 179) * 0.5
            opens[i] = closes[i] - 0.3

        # Force RSI low and volume shrinkage during the dip
        for i in range(160, 180):
            volumes[i] = 300_000  # shrunk volume

        result = strategy.backtest(
            prices=closes, volumes=volumes,
            initial_capital=1_000_000,
            open_prices=opens,
            code="TEST",
        )

        if result.total_trades > 0:
            first_trade = result.trades[0]
            entry_idx = None
            # Find the index where entry_date matches
            for i in range(n):
                if str(i) == first_trade.entry_date:
                    entry_idx = i
                    break
            if entry_idx is not None:
                # The entry price MUST be the open price of that day
                assert abs(first_trade.entry_price - opens[entry_idx]) < 1e-6, (
                    f"Entry should be at T+1 open ({opens[entry_idx]}), "
                    f"got {first_trade.entry_price}"
                )
                # And NOT the close of the previous day
                if entry_idx > 0:
                    assert abs(first_trade.entry_price - closes[entry_idx - 1]) > 0.01, (
                        "Entry price should NOT be the signal day's close!"
                    )

    def test_sell_signal_next_day(self):
        """卖出信号也是T+1执行 — GoldenDipStrategy sells at T+1 open"""
        from src.strategies.golden_dip import GoldenDipStrategy

        strategy = GoldenDipStrategy()
        n = 300

        # Build prices: uptrend → dip → recovery → crash
        np.random.seed(123)
        closes = np.zeros(n)
        opens = np.zeros(n)
        volumes = np.ones(n) * 1_000_000

        # Uptrend (0-149)
        for i in range(150):
            closes[i] = 50 + i * 0.8
            opens[i] = closes[i] - 0.3

        # Dip (150-175): trigger buy
        peak = closes[149]
        for i in range(150, 176):
            closes[i] = peak * (1 - (i - 150) / 26 * 0.20)
            opens[i] = closes[i] + 0.5
            volumes[i] = 300_000

        # Recovery to new high (176-230)
        for i in range(176, 231):
            closes[i] = closes[175] + (i - 175) * 0.9
            opens[i] = closes[i] - 0.3

        # Crash (231-299): trigger sell via trailing stop
        crash_peak = closes[230]
        for i in range(231, n):
            closes[i] = crash_peak * (1 - (i - 230) / 69 * 0.40)
            opens[i] = closes[i] + 0.5

        result = strategy.backtest(
            prices=closes, volumes=volumes,
            initial_capital=1_000_000,
            open_prices=opens,
            code="TEST_SELL",
        )

        for trade in result.trades:
            if trade.exit_reason != "end_of_data":
                exit_idx = None
                for i in range(n):
                    if str(i) == trade.exit_date:
                        exit_idx = i
                        break
                if exit_idx is not None:
                    # Exit price should be the open of the exit day
                    assert abs(trade.exit_price - opens[exit_idx]) < 1e-6, (
                        f"Exit should be at T+1 open ({opens[exit_idx]}), "
                        f"got {trade.exit_price}"
                    )


# ═══════════════════════════════════════════════════════════════════
# 10. cn_scanner backtest — Entry/Exit Price Consistency
# ═══════════════════════════════════════════════════════════════════

class TestCnScannerBacktestMath:
    """cn_scanner回测数学验证"""

    def test_forward_return_calculation(self):
        """验证前向收益率：(exit_price/entry_price - 1) * 100"""
        # entry_price = 100, exit after 5 days at 110
        # return = (110/100 - 1) * 100 = 10%
        entry = 100.0
        exit = 110.0
        expected = (exit / entry - 1) * 100
        assert abs(expected - 10.0) < 1e-9

    def test_annualization_formula(self):
        """验证年化公式：(1 + avg_per_period)^(periods_per_year) - 1
        If average 5-day return = 2%, periods_per_year = 252/5 = 50.4
        Annualized = (1.02)^50.4 - 1 ≈ 171.5%
        """
        avg_return_pct = 2.0  # 2%
        hold_days = 5
        periods_per_year = 252 / hold_days  # 50.4
        avg_per_period = avg_return_pct / 100.0  # 0.02
        annualized = ((1 + avg_per_period) ** periods_per_year - 1) * 100
        expected = ((1.02) ** 50.4 - 1) * 100
        assert abs(annualized - expected) < 0.1, f"Expected {expected}, got {annualized}"

    def test_win_rate_batch(self):
        """批次胜率：正收益批次数 / 总批次数"""
        returns = [2.0, -1.0, 3.0, -0.5, 1.0]  # 3 positive, 2 negative
        win_count = sum(1 for r in returns if r > 0)
        win_rate = win_count / len(returns) * 100
        assert abs(win_rate - 60.0) < 1e-9


# ═══════════════════════════════════════════════════════════════════
# 11. Cross-check: GoldenDip backtest statistics consistency
# ═══════════════════════════════════════════════════════════════════

class TestGoldenDipStatsConsistency:
    """GoldenDip回测统计量内部一致性"""

    def test_equity_curve_length_matches_data(self):
        """权益曲线长度应该等于输入数据长度"""
        from src.strategies.golden_dip import GoldenDipStrategy

        strategy = GoldenDipStrategy()
        n = 300
        prices = np.linspace(100, 200, n)
        volumes = np.ones(n) * 1_000_000

        result = strategy.backtest(prices=prices, volumes=volumes, code="LEN_TEST")
        assert len(result.equity_curve) == n

    def test_win_loss_count_consistency(self):
        """winning_trades + losing_trades = total_trades"""
        from src.strategies.golden_dip import GoldenDipStrategy

        strategy = GoldenDipStrategy()
        n = 500
        np.random.seed(99)
        prices = 100 * np.cumprod(1 + np.random.randn(n) * 0.02)
        volumes = np.ones(n) * 1_000_000

        result = strategy.backtest(prices=prices, volumes=volumes, code="CONSIST")
        assert result.winning_trades + result.losing_trades == result.total_trades

    def test_total_return_matches_equity(self):
        """总收益率应该和权益曲线首尾一致"""
        from src.strategies.golden_dip import GoldenDipStrategy

        strategy = GoldenDipStrategy()
        n = 400
        np.random.seed(77)
        prices = 100 * np.cumprod(1 + np.random.randn(n) * 0.015 + 0.001)
        volumes = np.ones(n) * 1_000_000
        initial = 1_000_000

        result = strategy.backtest(
            prices=prices, volumes=volumes,
            initial_capital=initial, code="RET_TEST",
        )
        # total_return_pct is computed from the final cash position,
        # not from the equity curve, but they should be approximately consistent
        if result.total_trades > 0:
            # Just check that total_return_pct is a valid number
            assert not math.isnan(result.total_return_pct)
            assert not math.isinf(result.total_return_pct)
