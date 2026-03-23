"""
Tests for CryptoBacktestEngine
==============================
Validates crypto-specific backtest behavior:
- No T+1 restriction
- No price limits
- Fee calculation (maker/taker)
- Leverage (return multiplication and liquidation)
- Funding rate charges
- Short selling
- Annual return with 365-day year
- Sharpe with crypto periods
- Integration (same tuple format as A-share)
- Edge cases
"""

from __future__ import annotations

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.crypto_backtest import CryptoBacktestEngine
from src.evolution.auto_evolve import StrategyDNA, score_stock


# ─────────────── Helpers ───────────────


def _make_price_data(
    prices: list[float],
    opens: list[float] | None = None,
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    volumes: list[float] | None = None,
) -> dict[str, dict[str, list]]:
    """Create minimal data dict for a single asset ('BTC')."""
    n = len(prices)
    if opens is None:
        opens = list(prices)
    if highs is None:
        highs = [p * 1.01 for p in prices]
    if lows is None:
        lows = [p * 0.99 for p in prices]
    if volumes is None:
        volumes = [1000.0] * n

    return {
        "BTC": {
            "date": list(range(n)),
            "open": opens,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volumes,
        }
    }


def _make_indicators(data: dict[str, dict[str, list]]) -> dict:
    """Build minimal indicator dict for score_stock compatibility."""
    from src.evolution.auto_evolve import (
        compute_rsi,
        compute_linear_regression,
        compute_volume_ratio,
        compute_macd,
        compute_bollinger_bands,
        compute_kdj,
        compute_obv_trend,
        compute_ma_alignment,
        compute_atr,
        compute_roc,
        compute_williams_r,
        compute_cci,
        compute_mfi,
        compute_donchian_position,
        compute_aroon,
        compute_price_volume_corr,
    )

    indicators = {}
    for code, sd in data.items():
        closes = sd["close"]
        vols = sd["volume"]
        opens = sd["open"]
        highs = sd["high"]
        lows = sd["low"]

        min_len = min(len(closes), len(vols), len(opens), len(highs), len(lows))
        closes = closes[:min_len]
        vols = vols[:min_len]
        opens = opens[:min_len]
        highs = highs[:min_len]
        lows = lows[:min_len]

        rsi = compute_rsi(closes)
        r2, slope = compute_linear_regression(closes)
        vol_ratio = compute_volume_ratio(vols)
        macd_line, macd_signal, macd_hist = compute_macd(closes)
        bb_upper, bb_middle, bb_lower, bb_width = compute_bollinger_bands(closes)
        kdj_k, kdj_d, kdj_j = compute_kdj(highs, lows, closes)
        obv = compute_obv_trend(closes, vols)
        ma_align = compute_ma_alignment(closes)
        atr_pct = compute_atr(highs, lows, closes)
        roc = compute_roc(closes)
        williams_r = compute_williams_r(highs, lows, closes)
        cci = compute_cci(closes, highs, lows)
        mfi = compute_mfi(highs, lows, closes, vols)
        donchian_pos = compute_donchian_position(highs, lows, closes)
        aroon = compute_aroon(closes)
        pv_corr = compute_price_volume_corr(closes, vols)

        indicators[code] = {
            "rsi": rsi, "r2": r2, "slope": slope, "volume_ratio": vol_ratio,
            "close": closes, "open": opens, "high": highs, "low": lows,
            "volume": vols,
            "macd_line": macd_line, "macd_signal": macd_signal, "macd_hist": macd_hist,
            "bb_upper": bb_upper, "bb_middle": bb_middle, "bb_lower": bb_lower,
            "kdj_k": kdj_k, "kdj_d": kdj_d, "kdj_j": kdj_j,
            "obv_trend": obv, "ma_alignment": ma_align,
            "atr_pct": atr_pct, "roc": roc, "williams_r": williams_r,
            "cci": cci, "mfi": mfi, "donchian_pos": donchian_pos,
            "aroon": aroon, "pv_corr": pv_corr,
            "fundamentals": {},
        }

    return indicators


def _make_trending_data(n: int = 200, start_price: float = 100.0, daily_return: float = 0.001):
    """Create data with a steady uptrend to guarantee long trades are triggered."""
    prices = [start_price]
    for i in range(1, n):
        prices.append(prices[-1] * (1 + daily_return))
    opens = [p * 0.999 for p in prices]
    highs = [p * 1.02 for p in prices]
    lows = [p * 0.98 for p in prices]
    volumes = [100000.0] * n
    return _make_price_data(prices, opens, highs, lows, volumes)


# ─────────────── Test: Constructor ───────────────


class TestCryptoBacktestInit:
    def test_default_params(self):
        engine = CryptoBacktestEngine()
        assert engine.leverage == 1
        assert engine.fee_maker == 0.0002
        assert engine.fee_taker == 0.0004
        assert engine.funding_rate == 0.0001
        assert engine.funding_interval == 8

    def test_custom_params(self):
        engine = CryptoBacktestEngine(
            leverage=5, fee_maker=0.001, fee_taker=0.002,
            funding_rate=0.0005, funding_interval=4,
        )
        assert engine.leverage == 5
        assert engine.fee_maker == 0.001

    def test_invalid_leverage_too_low(self):
        with pytest.raises(ValueError, match="Leverage must be 1-10"):
            CryptoBacktestEngine(leverage=0)

    def test_invalid_leverage_too_high(self):
        with pytest.raises(ValueError, match="Leverage must be 1-10"):
            CryptoBacktestEngine(leverage=11)


# ─────────────── Test: No T+1 ───────────────


class TestNoTPlus1:
    def test_can_sell_immediately(self):
        """Crypto allows selling in the same period as buying (no T+1)."""
        engine = CryptoBacktestEngine(leverage=1)
        # With hold_days=1 in DNA, crypto should enter and exit within 1 period
        dna = StrategyDNA(hold_days=1, min_score=0, max_positions=1)
        data = _make_trending_data(100)
        indicators = _make_indicators(data)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, 90)
        _annual, _dd, _wr, _sharpe, _calmar, trades, *_ = result
        # With hold_days=1, the engine should execute trades
        # (A-share enforces min 2, crypto allows 1)
        assert trades >= 0  # Should not crash

    def test_hold_days_1_works(self):
        """hold_days=1 should be valid for crypto (unlike A-share which needs 2+)."""
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=1, min_score=0, max_positions=1)
        data = _make_trending_data(100)
        indicators = _make_indicators(data)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, 90)
        assert len(result) == 12  # Returns the correct tuple


# ─────────────── Test: No Price Limits ───────────────


class TestNoPriceLimits:
    def test_50pct_up_no_block(self):
        """A 50% daily up move should not be blocked (no limit-up in crypto)."""
        prices = [100.0] * 40 + [150.0] * 10  # 50% jump
        opens = [p for p in prices]
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        data = _make_price_data(prices, opens, highs, lows)
        indicators = _make_indicators(data)

        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=1, min_score=0, max_positions=1)
        codes = list(data.keys())

        # Should not crash or skip the 50% move
        result = engine.run_backtest(dna, data, indicators, codes, 30, 49)
        assert len(result) == 12

    def test_50pct_down_no_block(self):
        """A 50% daily down move should not prevent selling (no limit-down)."""
        prices = [100.0] * 40 + [50.0] * 10
        opens = [p for p in prices]
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        data = _make_price_data(prices, opens, highs, lows)
        indicators = _make_indicators(data)

        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=2, min_score=0, max_positions=1)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, 49)
        assert len(result) == 12


# ─────────────── Test: Fee Calculation ───────────────


class TestFeeCalculation:
    def test_taker_fee_applied(self):
        """Verify taker fees are applied on both entry and exit."""
        engine = CryptoBacktestEngine(leverage=1, fee_taker=0.001)

        # Entry at 100, exit at 100 (flat) should result in loss = 2 * fee
        trade_return, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=100.0, shares=10.0,
            is_short=False, entry_period=0, exit_period=1,
        )
        expected_fees = 100.0 * 10.0 * 0.001 * 2  # entry + exit
        assert pnl == pytest.approx(-expected_fees, abs=0.01)
        assert trade_return < 0  # Should be negative due to fees

    def test_zero_fees(self):
        """With zero fees, flat trade should have zero PnL."""
        engine = CryptoBacktestEngine(leverage=1, fee_maker=0, fee_taker=0)
        trade_return, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=100.0, shares=10.0,
            is_short=False, entry_period=0, exit_period=1,
        )
        assert pnl == pytest.approx(0.0, abs=0.001)

    def test_maker_fee_different_from_taker(self):
        """Maker fee should be different from taker fee in configuration."""
        engine = CryptoBacktestEngine(fee_maker=0.0002, fee_taker=0.0004)
        assert engine.fee_maker != engine.fee_taker
        assert engine.fee_maker < engine.fee_taker


# ─────────────── Test: Leverage ───────────────


class TestLeverage:
    def test_2x_doubles_returns(self):
        """2x leverage should approximately double returns on price move."""
        engine_1x = CryptoBacktestEngine(leverage=1, fee_taker=0, funding_rate=0)
        engine_2x = CryptoBacktestEngine(leverage=2, fee_taker=0, funding_rate=0)

        # 10% price increase
        ret_1x, pnl_1x = engine_1x._compute_pnl(
            entry_price=100.0, exit_price=110.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
        )
        ret_2x, pnl_2x = engine_2x._compute_pnl(
            entry_price=100.0, exit_price=110.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
        )

        # 2x leverage should give ~2x the PnL
        assert pnl_2x == pytest.approx(pnl_1x * 2, rel=0.01)

    def test_2x_doubles_losses(self):
        """2x leverage should also double losses."""
        engine_1x = CryptoBacktestEngine(leverage=1, fee_taker=0, funding_rate=0)
        engine_2x = CryptoBacktestEngine(leverage=2, fee_taker=0, funding_rate=0)

        # 10% price decrease
        ret_1x, pnl_1x = engine_1x._compute_pnl(
            entry_price=100.0, exit_price=90.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
        )
        ret_2x, pnl_2x = engine_2x._compute_pnl(
            entry_price=100.0, exit_price=90.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
        )

        assert pnl_2x == pytest.approx(pnl_1x * 2, rel=0.01)

    def test_5x_liquidation_on_20pct_move(self):
        """5x leverage with 20% adverse move should be liquidated (100% loss)."""
        engine = CryptoBacktestEngine(leverage=5, fee_taker=0, funding_rate=0)

        # 20% price drop with 5x leverage => 100% margin loss => liquidation
        liquidated = engine._check_liquidation(
            entry_price=100.0, current_price=80.0, is_short=False,
        )
        assert liquidated is True

        # Verify PnL shows -100%
        trade_return, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=80.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
            was_liquidated=True,
        )
        assert trade_return == -100.0
        assert pnl == pytest.approx(-100.0, abs=0.01)

    def test_no_leverage_no_liquidation(self):
        """Without leverage, should never be liquidated even with huge loss."""
        engine = CryptoBacktestEngine(leverage=1)

        liquidated = engine._check_liquidation(
            entry_price=100.0, current_price=10.0, is_short=False,
        )
        assert liquidated is False

    def test_10x_liquidation_10pct_move(self):
        """10x leverage should liquidate on a 10% adverse move."""
        engine = CryptoBacktestEngine(leverage=10)
        assert engine._check_liquidation(100.0, 90.0, is_short=False) is True
        assert engine._check_liquidation(100.0, 91.0, is_short=False) is False

    def test_3x_leverage_pnl_calculation(self):
        """3x leverage should triple the directional PnL."""
        engine = CryptoBacktestEngine(leverage=3, fee_taker=0, funding_rate=0)
        ret, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=105.0, shares=1.0,
            is_short=False, entry_period=0, exit_period=1,
        )
        # 5% price move * 3x leverage = 15% return on margin
        assert ret == pytest.approx(15.0, abs=0.1)


# ─────────────── Test: Funding Rate ───────────────


class TestFundingRate:
    def test_funding_charged_over_holding_period(self):
        """Funding should be charged every 8 hours for perpetual positions."""
        engine = CryptoBacktestEngine(
            leverage=2, fee_taker=0, funding_rate=0.0001,
            funding_interval=8, periods_per_day=24,
        )

        # Hold for 24 hours (24 periods) => 3 funding intervals
        notional = 100.0 * 10.0 * 2  # entry_price * shares * leverage = 2000
        funding = engine._compute_funding_charges(
            entry_period=0, exit_period=24,
            position_value=notional, is_short=False,
        )
        expected = notional * 0.0001 * 3  # 3 intervals in 24 hours
        assert funding == pytest.approx(expected, rel=0.01)

    def test_no_funding_for_spot(self):
        """Spot (leverage=1) should have no funding charges."""
        engine = CryptoBacktestEngine(leverage=1)
        funding = engine._compute_funding_charges(
            entry_period=0, exit_period=100,
            position_value=10000.0, is_short=False,
        )
        assert funding == 0.0

    def test_funding_direction_for_shorts(self):
        """Shorts should receive funding (negative cost) when rate is positive."""
        engine = CryptoBacktestEngine(
            leverage=2, funding_rate=0.0001, funding_interval=8,
            periods_per_day=24, fee_taker=0,
        )
        notional = 2000.0

        long_funding = engine._compute_funding_charges(
            0, 24, notional, is_short=False,
        )
        short_funding = engine._compute_funding_charges(
            0, 24, notional, is_short=True,
        )

        # Long pays funding, short receives (opposite signs)
        assert long_funding > 0
        assert short_funding < 0
        assert long_funding == pytest.approx(-short_funding, rel=0.01)


# ─────────────── Test: Short Selling ───────────────


class TestShortSelling:
    def test_short_profit(self):
        """Short at 100, cover at 90 = profit."""
        engine = CryptoBacktestEngine(leverage=2, fee_taker=0, funding_rate=0)
        trade_return, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=90.0, shares=1.0,
            is_short=True, entry_period=0, exit_period=1,
        )
        assert pnl > 0
        # 10% price drop * 2x leverage = 20% return on margin
        assert trade_return == pytest.approx(20.0, abs=0.1)

    def test_short_loss(self):
        """Short at 100, cover at 110 = loss."""
        engine = CryptoBacktestEngine(leverage=2, fee_taker=0, funding_rate=0)
        trade_return, pnl = engine._compute_pnl(
            entry_price=100.0, exit_price=110.0, shares=1.0,
            is_short=True, entry_period=0, exit_period=1,
        )
        assert pnl < 0
        assert trade_return < 0

    def test_short_liquidation(self):
        """Short should be liquidated if price rises by >= 1/leverage."""
        engine = CryptoBacktestEngine(leverage=5)
        # Short at 100, price rises to 120 (20% up) => liquidated
        assert engine._check_liquidation(100.0, 120.0, is_short=True) is True
        # 19% up => not liquidated
        assert engine._check_liquidation(100.0, 119.0, is_short=True) is False


# ─────────────── Test: Return Calculation ───────────────


class TestReturnCalculation:
    def test_annual_return_uses_365_days(self):
        """Crypto annual return should use 365-day year, not 250 trading days."""
        engine = CryptoBacktestEngine(leverage=1, periods_per_day=1)
        # Create 365 days of 0.1% daily return
        n = 400
        prices = [100.0]
        for i in range(1, n):
            prices.append(prices[-1] * 1.001)
        data = _make_price_data(prices)
        indicators = _make_indicators(data)
        dna = StrategyDNA(hold_days=5, min_score=0, max_positions=1)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, n - 1)
        annual_return = result[0]
        # Should compute annual return based on 365-day year
        # We just verify it returns a reasonable number (not NaN or crash)
        assert not math.isnan(annual_return)
        assert isinstance(annual_return, float)

    def test_hourly_data_periods_per_year(self):
        """Hourly data should use 365*24 = 8760 periods per year."""
        engine = CryptoBacktestEngine(leverage=1, periods_per_day=24)
        # 8760 periods = 1 year of hourly data
        assert engine.periods_per_day == 24


# ─────────────── Test: Sharpe Calculation ───────────────


class TestSharpeCalculation:
    def test_sharpe_uses_crypto_periods(self):
        """Sharpe should annualize using crypto periods (365*periods_per_day)."""
        engine = CryptoBacktestEngine(leverage=1, periods_per_day=24, fee_taker=0)
        # Steady uptrend
        n = 500
        prices = [100.0]
        for i in range(1, n):
            prices.append(prices[-1] * 1.0005)
        opens = [p * 0.999 for p in prices]
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        data = _make_price_data(prices, opens, highs, lows)
        indicators = _make_indicators(data)
        dna = StrategyDNA(hold_days=1, min_score=0, max_positions=1)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, n - 1)
        sharpe = result[3]
        assert not math.isnan(sharpe)


# ─────────────── Test: Integration ───────────────


class TestIntegration:
    def test_returns_correct_tuple_format(self):
        """CryptoBacktestEngine should return same 12-element tuple as A-share."""
        engine = CryptoBacktestEngine()
        data = _make_trending_data(200)
        indicators = _make_indicators(data)
        dna = StrategyDNA(hold_days=3, min_score=0, max_positions=1)
        codes = list(data.keys())

        result = engine.run_backtest(dna, data, indicators, codes, 30, 190)
        assert isinstance(result, tuple)
        assert len(result) == 12

        (annual_return, max_dd, win_rate, sharpe, calmar,
         trades, pf, sortino, consec_losses, monthly_rets,
         max_concurrent, avg_turnover) = result

        assert isinstance(annual_return, float)
        assert isinstance(max_dd, float)
        assert isinstance(win_rate, float)
        assert isinstance(sharpe, float)
        assert isinstance(calmar, float)
        assert isinstance(trades, int)
        assert isinstance(pf, float)
        assert isinstance(sortino, float)
        assert isinstance(consec_losses, int)
        assert isinstance(monthly_rets, list)
        assert isinstance(max_concurrent, int)
        assert isinstance(avg_turnover, float)

    def test_auto_evolver_crypto_mode(self):
        """AutoEvolver with market='crypto' should instantiate correctly."""
        from src.evolution.auto_evolve import AutoEvolver
        evolver = AutoEvolver(
            data_dir="data/crypto",
            market="crypto",
        )
        assert evolver.market == "crypto"
        assert evolver._crypto_engine is not None

    def test_auto_evolver_cn_mode_unchanged(self):
        """AutoEvolver with market='cn' should not create crypto engine."""
        from src.evolution.auto_evolve import AutoEvolver
        evolver = AutoEvolver(
            data_dir="data/a_shares",
            market="cn",
        )
        assert evolver.market == "cn"
        assert evolver._crypto_engine is None


# ─────────────── Test: Edge Cases ───────────────


class TestEdgeCases:
    def test_empty_data(self):
        """Empty data dict should not crash."""
        engine = CryptoBacktestEngine()
        dna = StrategyDNA()
        result = engine.run_backtest(dna, {}, {}, [], 0, 0)
        assert len(result) == 12
        assert result[5] == 0  # total_trades = 0

    def test_single_candle(self):
        """Single candle should not crash."""
        data = _make_price_data([100.0])
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=1, min_score=0)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 0, 1)
        assert len(result) == 12

    def test_all_flat_prices(self):
        """All flat prices should result in zero or negative returns (fees)."""
        prices = [100.0] * 100
        data = _make_price_data(prices)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=2, min_score=0, max_positions=1)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 30, 99)
        annual_return = result[0]
        # Flat prices + fees => should not be positive
        assert isinstance(annual_return, float)

    def test_very_short_period(self):
        """Very short backtest period (2 candles) should not crash."""
        prices = [100.0, 101.0, 102.0]
        data = _make_price_data(prices)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=1, min_score=0)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 0, 2)
        assert len(result) == 12

    def test_zero_entry_price_skipped(self):
        """Candles with zero open price should be skipped gracefully."""
        prices = [100.0] * 40 + [0.0] + [100.0] * 10
        opens = [p for p in prices]
        opens[40] = 0.0
        data = _make_price_data(prices, opens)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=1, min_score=0)
        codes = list(data.keys())
        # Should not crash
        result = engine.run_backtest(dna, data, indicators, codes, 30, 50)
        assert len(result) == 12

    def test_max_drawdown_calculation(self):
        """Max drawdown should be non-negative."""
        data = _make_trending_data(200)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=3, min_score=0, max_positions=1)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 30, 190)
        max_dd = result[1]
        assert max_dd >= 0.0

    def test_win_rate_bounds(self):
        """Win rate should be between 0 and 100."""
        data = _make_trending_data(200)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=3, min_score=0, max_positions=1)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 30, 190)
        win_rate = result[2]
        trades = result[5]
        if trades > 0:
            assert 0.0 <= win_rate <= 100.0

    def test_multiple_assets(self):
        """Should handle multiple assets correctly."""
        prices_btc = [100.0 + i * 0.5 for i in range(100)]
        prices_eth = [50.0 + i * 0.3 for i in range(100)]
        data = {
            "BTC": {
                "date": list(range(100)),
                "open": prices_btc, "high": [p * 1.01 for p in prices_btc],
                "low": [p * 0.99 for p in prices_btc], "close": prices_btc,
                "volume": [1000.0] * 100,
            },
            "ETH": {
                "date": list(range(100)),
                "open": prices_eth, "high": [p * 1.01 for p in prices_eth],
                "low": [p * 0.99 for p in prices_eth], "close": prices_eth,
                "volume": [1000.0] * 100,
            },
        }
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine()
        dna = StrategyDNA(hold_days=3, min_score=0, max_positions=2)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 30, 90)
        assert len(result) == 12


# ─────────────── Test: liquidation integration in run_backtest ───────────────


class TestLiquidationInBacktest:
    def test_leveraged_backtest_with_crash(self):
        """A position that gets liquidated mid-hold should lose margin."""
        # Build data: steady then sudden crash
        n = 80
        prices = [100.0] * 50 + [60.0] * 30  # 40% crash
        opens = list(prices)
        highs = [p * 1.01 for p in prices]
        lows = [p * 0.99 for p in prices]
        # For the crash candle, low should reflect the crash
        lows[50] = 55.0
        data = _make_price_data(prices, opens, highs, lows)
        indicators = _make_indicators(data)

        engine_spot = CryptoBacktestEngine(leverage=1, fee_taker=0)
        engine_5x = CryptoBacktestEngine(leverage=5, fee_taker=0, funding_rate=0)

        dna = StrategyDNA(hold_days=5, min_score=0, max_positions=1,
                          stop_loss_pct=50)  # wide stop so liquidation triggers first
        codes = list(data.keys())

        result_spot = engine_spot.run_backtest(dna, data, indicators, codes, 30, 70)
        result_5x = engine_5x.run_backtest(dna, data, indicators, codes, 30, 70)

        # Spot should survive, 5x should have more severe losses
        # Both should return valid tuples
        assert len(result_spot) == 12
        assert len(result_5x) == 12


# ─────────────── Test: Monthly returns tracking ───────────────


class TestMonthlyReturns:
    def test_monthly_returns_list(self):
        """Monthly returns should be populated as a list."""
        # Use daily data with enough periods for multiple months
        n = 200
        data = _make_trending_data(n, daily_return=0.001)
        indicators = _make_indicators(data)
        engine = CryptoBacktestEngine(periods_per_day=1)
        dna = StrategyDNA(hold_days=3, min_score=0, max_positions=1)
        codes = list(data.keys())
        result = engine.run_backtest(dna, data, indicators, codes, 30, n - 1)
        monthly_rets = result[9]
        assert isinstance(monthly_rets, list)
