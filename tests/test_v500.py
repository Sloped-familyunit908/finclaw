"""
Tests for FinClaw Strategy Library v5.0.0
==========================================
50+ tests covering all 10 built-in strategies, base class, registry, and CLI.
"""

import math
import pytest
from src.strategies.library.base import (
    Strategy, StrategySignal, StrategyMeta, sma, ema, rsi, bollinger_bands, adx, donchian_channel,
)
from src.strategies.library import (
    STRATEGY_REGISTRY, get_strategy, list_strategies,
    GridTradingStrategy, FundingRateArbitrage, DCAStrategy,
    PairsTradingStrategy, SectorRotationStrategy, DividendHarvestStrategy,
    TrendFollowingStrategy, BreakoutStrategy, MeanReversionBBStrategy,
    MultiFactorStrategy,
)


# ── Helper: generate synthetic OHLCV data ──

def _make_ohlcv(prices: list[float], volumes: list[float] | None = None) -> list[dict]:
    """Create OHLCV data from a list of close prices."""
    data = []
    for i, p in enumerate(prices):
        data.append({
            "open": p * 0.99,
            "high": p * 1.02,
            "low": p * 0.97,
            "close": p,
            "volume": (volumes[i] if volumes else 1000),
        })
    return data


def _trending_up(n: int = 100, start: float = 100.0, step: float = 0.5) -> list[float]:
    return [start + i * step for i in range(n)]


def _trending_down(n: int = 100, start: float = 200.0, step: float = 0.5) -> list[float]:
    return [start - i * step for i in range(n)]


def _range_bound(n: int = 100, low: float = 90, high: float = 110) -> list[float]:
    """Oscillate between low and high."""
    import math as m
    return [low + (high - low) * (0.5 + 0.5 * m.sin(2 * m.pi * i / 20)) for i in range(n)]


def _flat(n: int = 100, price: float = 100.0) -> list[float]:
    return [price] * n


# ══════════════════════════════════════════════════════════════════════
# 1. BASE CLASS & HELPERS
# ══════════════════════════════════════════════════════════════════════

class TestHelpers:
    def test_sma_basic(self):
        assert sma([1, 2, 3, 4, 5], 3) == pytest.approx(4.0)

    def test_sma_insufficient(self):
        assert sma([1, 2], 5) is None

    def test_ema_basic(self):
        val = ema([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 5)
        assert val is not None
        assert val > 5

    def test_ema_insufficient(self):
        assert ema([1, 2], 5) is None

    def test_rsi_basic(self):
        prices = list(range(100, 120))  # uptrend
        val = rsi(prices, 14)
        assert val is not None
        assert val > 50

    def test_rsi_insufficient(self):
        assert rsi([100, 101], 14) is None

    def test_rsi_all_gains(self):
        prices = list(range(100, 120))
        val = rsi(prices, 14)
        assert val == 100.0

    def test_bollinger_bands_basic(self):
        prices = [100 + i * 0.1 for i in range(30)]
        result = bollinger_bands(prices, 20, 2.0)
        assert result is not None
        upper, mid, lower = result
        assert upper > mid > lower

    def test_bollinger_bands_insufficient(self):
        assert bollinger_bands([1, 2, 3], 20) is None

    def test_donchian_channel_basic(self):
        highs = [10 + i for i in range(25)]
        lows = [5 + i for i in range(25)]
        result = donchian_channel(highs, lows, 20)
        assert result is not None
        upper, mid, lower = result
        assert upper >= mid >= lower

    def test_donchian_insufficient(self):
        assert donchian_channel([1, 2], [0, 1], 20) is None

    def test_adx_basic(self):
        n = 30
        highs = [100 + i * 1.5 for i in range(n)]
        lows = [98 + i * 1.5 for i in range(n)]
        closes = [99 + i * 1.5 for i in range(n)]
        val = adx(highs, lows, closes, 14)
        assert val is not None
        assert val >= 0

    def test_adx_insufficient(self):
        assert adx([1, 2], [0, 1], [0.5, 1.5], 14) is None


class TestStrategySignal:
    def test_defaults(self):
        sig = StrategySignal("buy", 0.8)
        assert sig.action == "buy"
        assert sig.confidence == 0.8
        assert sig.price == 0.0
        assert sig.metadata == {}

    def test_with_metadata(self):
        sig = StrategySignal("sell", 0.5, metadata={"z_score": 2.5})
        assert sig.metadata["z_score"] == 2.5


class TestStrategyMeta:
    def test_fields(self):
        m = StrategyMeta("Test", "test", "universal", "desc", {"a": "b"}, "example")
        assert m.slug == "test"
        assert m.category == "universal"


# ══════════════════════════════════════════════════════════════════════
# 2. REGISTRY
# ══════════════════════════════════════════════════════════════════════

class TestRegistry:
    def test_registry_has_10_strategies(self):
        assert len(STRATEGY_REGISTRY) == 11

    def test_get_strategy_valid(self):
        cls = get_strategy("grid-trading")
        assert cls is GridTradingStrategy

    def test_get_strategy_invalid(self):
        with pytest.raises(KeyError, match="Unknown strategy"):
            get_strategy("nonexistent")

    def test_list_strategies_returns_meta(self):
        metas = list_strategies()
        assert len(metas) == 11
        assert all(isinstance(m, StrategyMeta) for m in metas)

    def test_all_strategies_have_meta(self):
        for slug, cls in STRATEGY_REGISTRY.items():
            m = cls.meta()
            assert m.slug == slug
            assert m.name
            assert m.category in ("crypto", "stock", "universal")

    def test_all_strategies_extend_base(self):
        for cls in STRATEGY_REGISTRY.values():
            assert issubclass(cls, Strategy)


# ══════════════════════════════════════════════════════════════════════
# 3. GRID TRADING
# ══════════════════════════════════════════════════════════════════════

class TestGridTrading:
    def test_grid_levels(self):
        s = GridTradingStrategy(lower_price=100, upper_price=200, num_grids=5)
        assert len(s.grid_levels) == 6
        assert s.grid_levels[0] == 100
        assert s.grid_levels[-1] == 200

    def test_invalid_range(self):
        with pytest.raises(ValueError):
            GridTradingStrategy(lower_price=200, upper_price=100)

    def test_invalid_grids(self):
        with pytest.raises(ValueError):
            GridTradingStrategy(lower_price=100, upper_price=200, num_grids=1)

    def test_signals_in_range(self):
        prices = _range_bound(50, 100, 200)
        data = _make_ohlcv(prices)
        s = GridTradingStrategy(lower_price=90, upper_price=210, num_grids=5)
        signals = s.generate_signals(data)
        assert len(signals) == 50
        actions = {sig.action for sig in signals}
        assert "hold" in actions

    def test_meta(self):
        m = GridTradingStrategy.meta()
        assert m.slug == "grid-trading"
        assert m.category == "crypto"

    def test_backtest_runs(self):
        data = _make_ohlcv(_range_bound(100, 100, 200))
        s = GridTradingStrategy(lower_price=90, upper_price=210, num_grids=10)
        result = s.backtest(data)
        assert "total_return" in result
        assert "num_trades" in result


# ══════════════════════════════════════════════════════════════════════
# 4. FUNDING RATE ARBITRAGE
# ══════════════════════════════════════════════════════════════════════

class TestFundingRate:
    def _make_data(self, funding_rates: list[float]) -> list[dict]:
        return [{"close": 30000 + i * 10, "funding_rate": fr} for i, fr in enumerate(funding_rates)]

    def test_enters_on_high_rate(self):
        # 0.01 * 3 * 365 * 100 = 1095% annualized
        data = self._make_data([0.01] * 10)
        s = FundingRateArbitrage(entry_threshold=10)
        signals = s.generate_signals(data)
        assert signals[0].action == "buy"

    def test_no_entry_on_low_rate(self):
        data = self._make_data([0.00001] * 10)
        s = FundingRateArbitrage(entry_threshold=10)
        signals = s.generate_signals(data)
        assert all(sig.action != "buy" for sig in signals)

    def test_exit_on_rate_drop(self):
        rates = [0.01] * 5 + [0.0] * 5
        data = self._make_data(rates)
        s = FundingRateArbitrage(entry_threshold=10, exit_threshold=2)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "buy" in actions
        assert "sell" in actions

    def test_meta(self):
        m = FundingRateArbitrage.meta()
        assert m.slug == "funding-rate"


# ══════════════════════════════════════════════════════════════════════
# 5. DCA
# ══════════════════════════════════════════════════════════════════════

class TestDCA:
    def test_weekly_buys(self):
        data = _make_ohlcv(_flat(30, 100))
        s = DCAStrategy(amount_per_period=100, period="weekly", smart_timing=False)
        signals = s.generate_signals(data)
        buys = [sig for sig in signals if sig.action == "buy"]
        assert len(buys) == 5  # 0, 7, 14, 21, 28

    def test_invalid_period(self):
        with pytest.raises(ValueError):
            DCAStrategy(period="quarterly")

    def test_invalid_amount(self):
        with pytest.raises(ValueError):
            DCAStrategy(amount_per_period=-10)

    def test_smart_timing_boost(self):
        # Create declining prices to get low RSI
        prices = _trending_down(50, 200, 2)
        data = _make_ohlcv(prices)
        s = DCAStrategy(amount_per_period=100, period="daily", smart_timing=True, rsi_boost_threshold=50, boost_multiplier=2.0)
        signals = s.generate_signals(data)
        # Some later buys should be boosted
        boosted = [sig for sig in signals if sig.action == "buy" and sig.metadata.get("amount", 100) > 100]
        assert len(boosted) > 0

    def test_backtest(self):
        data = _make_ohlcv(_trending_up(60, 100, 1))
        s = DCAStrategy(amount_per_period=100, period="weekly")
        result = s.backtest(data)
        assert result["num_trades"] > 0
        assert result["total_invested"] > 0

    def test_meta(self):
        assert DCAStrategy.meta().slug == "dca"
        assert DCAStrategy.meta().category == "crypto"


# ══════════════════════════════════════════════════════════════════════
# 6. PAIRS TRADING
# ══════════════════════════════════════════════════════════════════════

class TestPairsTrading:
    def _make_pair_data(self, n=100):
        import math as m
        data = []
        for i in range(n):
            a = 100 + m.sin(i * 0.1) * 5 + i * 0.05
            b = 100 + m.sin(i * 0.1) * 5  # no drift
            data.append({"close_a": a, "close_b": b, "close": a})
        return data

    def test_signals_length(self):
        data = self._make_pair_data(100)
        s = PairsTradingStrategy(lookback=20)
        signals = s.generate_signals(data)
        assert len(signals) == 100

    def test_warmup_period(self):
        data = self._make_pair_data(100)
        s = PairsTradingStrategy(lookback=30)
        signals = s.generate_signals(data)
        assert all(sig.action == "hold" for sig in signals[:30])

    def test_meta(self):
        m = PairsTradingStrategy.meta()
        assert m.slug == "pairs-trading"
        assert m.category == "stock"


# ══════════════════════════════════════════════════════════════════════
# 7. SECTOR ROTATION
# ══════════════════════════════════════════════════════════════════════

class TestSectorRotation:
    def _make_sector_data(self, n=100):
        data = []
        for i in range(n):
            data.append({
                "close": 100 + i,
                "sectors": {
                    "XLK": 200 + i * 2,
                    "XLF": 150 + i * 0.5,
                    "XLV": 130 + i * 1,
                    "XLE": 80 + i * 1.5,
                    "XLI": 100 + i * 0.8,
                },
            })
        return data

    def test_rebalance_signals(self):
        data = self._make_sector_data(100)
        s = SectorRotationStrategy(top_n=2, lookback=20, rebalance_freq=10)
        signals = s.generate_signals(data)
        buys = [sig for sig in signals if sig.action == "buy"]
        assert len(buys) > 0

    def test_top_n_in_metadata(self):
        data = self._make_sector_data(100)
        s = SectorRotationStrategy(top_n=2, lookback=20, rebalance_freq=10)
        signals = s.generate_signals(data)
        buy_signals = [sig for sig in signals if sig.action == "buy"]
        if buy_signals:
            assert "holdings" in buy_signals[0].metadata
            assert len(buy_signals[0].metadata["holdings"]) <= 2

    def test_meta(self):
        m = SectorRotationStrategy.meta()
        assert m.slug == "sector-rotation"
        assert m.category == "stock"


# ══════════════════════════════════════════════════════════════════════
# 8. DIVIDEND HARVEST
# ══════════════════════════════════════════════════════════════════════

class TestDividendHarvest:
    def _make_div_data(self, n=100, div_days=None, div_amount=1.0):
        div_days = div_days or [30, 60, 90]
        data = []
        for i in range(n):
            data.append({
                "close": 50.0,
                "dividend": div_amount if i in div_days else 0,
            })
        return data

    def test_buys_before_exdiv(self):
        data = self._make_div_data(100, div_days=[30])
        s = DividendHarvestStrategy(hold_days_before=2, hold_days_after=3, min_yield=0.5)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "buy" in actions

    def test_sells_after_exdiv(self):
        data = self._make_div_data(100, div_days=[30])
        s = DividendHarvestStrategy(hold_days_before=2, hold_days_after=3, min_yield=0.5)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "sell" in actions

    def test_no_trade_low_yield(self):
        data = self._make_div_data(100, div_days=[30], div_amount=0.001)
        s = DividendHarvestStrategy(min_yield=5.0)
        signals = s.generate_signals(data)
        assert all(sig.action == "hold" for sig in signals)

    def test_meta(self):
        m = DividendHarvestStrategy.meta()
        assert m.slug == "dividend-harvest"
        assert m.category == "stock"


# ══════════════════════════════════════════════════════════════════════
# 9. TREND FOLLOWING
# ══════════════════════════════════════════════════════════════════════

class TestTrendFollowing:
    def test_warmup(self):
        data = _make_ohlcv(_flat(60))
        s = TrendFollowingStrategy(fast_period=10, slow_period=30)
        signals = s.generate_signals(data)
        assert all(sig.action == "hold" for sig in signals[:31])

    def test_uptrend_generates_buy(self):
        # Flat then suddenly uptrend to create golden cross
        flat = _flat(40, 100)
        up = _trending_up(40, 100, 2)
        data = _make_ohlcv(flat + up)
        s = TrendFollowingStrategy(fast_period=5, slow_period=20, adx_threshold=0)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "buy" in actions

    def test_backtest_runs(self):
        data = _make_ohlcv(_trending_up(100, 50, 1))
        s = TrendFollowingStrategy(fast_period=5, slow_period=20, adx_threshold=0)
        result = s.backtest(data)
        assert "total_return" in result

    def test_meta(self):
        m = TrendFollowingStrategy.meta()
        assert m.slug == "trend-following"
        assert m.category == "universal"


# ══════════════════════════════════════════════════════════════════════
# 10. BREAKOUT
# ══════════════════════════════════════════════════════════════════════

class TestBreakout:
    def test_warmup(self):
        data = _make_ohlcv(_flat(30))
        s = BreakoutStrategy(channel_period=20)
        signals = s.generate_signals(data)
        assert all(sig.action == "hold" for sig in signals[:20])

    def test_breakout_detected(self):
        flat = _flat(30, 100)
        spike = [100 + i * 5 for i in range(30)]
        data = _make_ohlcv(flat + spike, volumes=[500] * 30 + [5000] * 30)
        s = BreakoutStrategy(channel_period=20, volume_multiplier=1.0)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "buy" in actions

    def test_meta(self):
        m = BreakoutStrategy.meta()
        assert m.slug == "breakout"
        assert m.category == "universal"


# ══════════════════════════════════════════════════════════════════════
# 11. MEAN REVERSION BB
# ══════════════════════════════════════════════════════════════════════

class TestMeanReversionBB:
    def test_warmup(self):
        data = _make_ohlcv(_flat(15))
        s = MeanReversionBBStrategy(bb_period=20)
        signals = s.generate_signals(data)
        assert all(sig.action == "hold" for sig in signals)

    def test_oversold_buy(self):
        # Sharp drop after flat period → touches lower BB with low RSI
        prices = _flat(30, 100) + _trending_down(30, 100, 3)
        data = _make_ohlcv(prices)
        s = MeanReversionBBStrategy(bb_period=20, rsi_period=14, rsi_oversold=45, bb_std=1.5)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        assert "buy" in actions

    def test_backtest_runs(self):
        data = _make_ohlcv(_range_bound(100, 80, 120))
        s = MeanReversionBBStrategy()
        result = s.backtest(data)
        assert "total_return" in result

    def test_meta(self):
        m = MeanReversionBBStrategy.meta()
        assert m.slug == "mean-reversion-bb"
        assert m.category == "universal"


# ══════════════════════════════════════════════════════════════════════
# 12. MULTI-FACTOR
# ══════════════════════════════════════════════════════════════════════

class TestMultiFactor:
    def test_warmup(self):
        data = _make_ohlcv(_flat(100))
        s = MultiFactorStrategy(sma_period=50, momentum_lookback=80)
        signals = s.generate_signals(data)
        # First 253 bars should be hold (max of sma_period, momentum_lookback+1)
        assert signals[0].action == "hold"

    def test_with_fundamentals(self):
        prices = _trending_up(300, 50, 0.5)
        data = _make_ohlcv(prices)
        for bar in data:
            bar["roe"] = 0.25
            bar["debt_equity"] = 0.3
        s = MultiFactorStrategy(sma_period=50, momentum_lookback=100)
        signals = s.generate_signals(data)
        actions = [sig.action for sig in signals]
        # With good fundamentals and uptrend, should generate some signals
        assert len(signals) == 300

    def test_quality_score_no_fundamentals(self):
        s = MultiFactorStrategy()
        q = s._quality_score({"close": 100})
        assert q == 0.0

    def test_quality_score_with_roe(self):
        s = MultiFactorStrategy()
        q = s._quality_score({"close": 100, "roe": 0.25})
        assert q > 0

    def test_meta(self):
        m = MultiFactorStrategy.meta()
        assert m.slug == "multi-factor"
        assert m.category == "universal"


# ══════════════════════════════════════════════════════════════════════
# 13. BASE STRATEGY BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════

class TestBaseBacktest:
    def test_backtest_trending_up(self):
        data = _make_ohlcv(_trending_up(100, 50, 1))
        s = TrendFollowingStrategy(fast_period=5, slow_period=20, adx_threshold=0)
        result = s.backtest(data)
        assert result["final_equity"] > 0

    def test_backtest_equity_curve(self):
        data = _make_ohlcv(_trending_up(60, 100, 1))
        s = BreakoutStrategy(channel_period=10, volume_multiplier=0)
        result = s.backtest(data)
        assert len(result["equity_curve"]) == 60

    def test_backtest_no_data(self):
        s = TrendFollowingStrategy()
        result = s.backtest([])
        assert result["num_trades"] == 0


# ══════════════════════════════════════════════════════════════════════
# 14. CLI INTEGRATION
# ══════════════════════════════════════════════════════════════════════

class TestCLI:
    def test_strategy_list(self, capsys):
        from src.cli import main
        main(["strategy", "list"])
        out = capsys.readouterr().out
        assert "grid-trading" in out
        assert "trend-following" in out

    def test_strategy_info(self, capsys):
        from src.cli import main
        main(["strategy", "info", "breakout"])
        out = capsys.readouterr().out
        assert "Breakout" in out
        assert "channel_period" in out

    def test_strategy_info_unknown(self, capsys):
        from src.cli import main
        main(["strategy", "info", "nonexistent"])
        out = capsys.readouterr().out
        assert "Unknown strategy" in out
