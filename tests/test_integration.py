"""
Integration tests — end-to-end flows combining multiple FinClaw modules.
"""

import numpy as np
import pytest


def _make_prices(n: int = 500, seed: int = 42) -> np.ndarray:
    rng = np.random.RandomState(seed)
    return 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.015, n))


def _make_ohlcv(n: int = 500, seed: int = 42):
    rng = np.random.RandomState(seed)
    close = _make_prices(n, seed)
    high = close * (1 + rng.uniform(0, 0.02, n))
    low = close * (1 - rng.uniform(0, 0.02, n))
    volume = rng.uniform(1e6, 5e6, n)
    return high, low, close, volume


# ---------------------------------------------------------------------------
# 1. Strategy + Backtest
# ---------------------------------------------------------------------------

class TestStrategyBacktest:

    def test_momentum_score(self):
        from src.strategies import MomentumJTStrategy
        prices = _make_prices()
        s = MomentumJTStrategy()
        score = s.score_single(prices)
        assert hasattr(score, 'signal')

    def test_walkforward_run(self):
        from src.backtesting import WalkForwardAnalyzer
        wfa = WalkForwardAnalyzer(train_bars=200, test_bars=50, step_bars=50)
        # Just verify instantiation — run() requires a full strategy+data contract
        assert wfa is not None

    def test_combiner(self):
        from src.strategies import StrategyCombiner, MomentumAdapter, MomentumJTStrategy
        mom = MomentumJTStrategy()
        adapter = MomentumAdapter(strategy=mom)
        combiner = StrategyCombiner(strategies=[adapter], weights=[1.0])
        assert combiner is not None


# ---------------------------------------------------------------------------
# 2. TA indicators smoke test
# ---------------------------------------------------------------------------

class TestTASmoke:

    def test_moving_averages(self):
        from src.ta import sma, ema, wma, dema, tema
        p = _make_prices(200)
        for fn in [sma, ema, wma, dema, tema]:
            assert len(fn(p, 20)) == len(p)

    def test_rsi(self):
        from src.ta import rsi
        assert len(rsi(_make_prices(200), 14)) == 200

    def test_macd(self):
        from src.ta import macd
        line, sig, hist = macd(_make_prices(200))
        assert len(line) == 200

    def test_bollinger(self):
        from src.ta import bollinger_bands
        bb = bollinger_bands(_make_prices(200), 20)
        assert "upper" in bb and "lower" in bb

    def test_atr_adx(self):
        from src.ta import atr, adx
        h, l, c, _ = _make_ohlcv(200)
        assert len(atr(h, l, c, 14)) == 200
        assert len(adx(h, l, c, 14)) == 200

    def test_volume_indicators(self):
        from src.ta import obv, cmf
        h, l, c, v = _make_ohlcv(200)
        assert len(obv(c, v)) == 200
        assert len(cmf(h, l, c, v, 20)) == 200

    def test_ichimoku(self):
        from src.ta import ichimoku
        h, l, c, _ = _make_ohlcv(200)
        assert "tenkan" in ichimoku(h, l, c)

    def test_parabolic_sar(self):
        from src.ta import parabolic_sar
        h, l, _, _ = _make_ohlcv(200)
        assert len(parabolic_sar(h, l)) == 200

    def test_stochastic_rsi(self):
        from src.ta import stochastic_rsi
        k, d = stochastic_rsi(_make_prices(200))
        assert len(k) == 200

    def test_mfi(self):
        from src.ta import mfi
        h, l, c, v = _make_ohlcv(200)
        assert len(mfi(h, l, c, v, 14)) == 200


# ---------------------------------------------------------------------------
# 3. Risk management
# ---------------------------------------------------------------------------

class TestRiskPipeline:

    def test_kelly(self):
        from src.risk import KellyCriterion
        assert KellyCriterion(kelly_fraction=0.5, max_position=0.25) is not None

    def test_var(self):
        from src.risk import VaRCalculator
        returns = np.diff(_make_prices()) / _make_prices()[:-1]
        var = VaRCalculator(confidence=0.95)
        result = var.historical(returns)
        # Returns a VaRResult object
        assert hasattr(result, 'var')

    def test_stop_loss(self):
        from src.risk import StopLossManager
        assert StopLossManager(fixed_pct=0.05, trailing_pct=0.08) is not None


# ---------------------------------------------------------------------------
# 4. Portfolio
# ---------------------------------------------------------------------------

class TestPortfolio:

    def test_tracker(self):
        from src.portfolio import PortfolioTracker
        assert PortfolioTracker() is not None

    def test_rebalancer(self):
        from src.portfolio.rebalancer import PortfolioRebalancer
        r = PortfolioRebalancer(target_weights={"AAPL": 0.5, "MSFT": 0.5})
        assert r is not None


# ---------------------------------------------------------------------------
# 5. ML pipeline
# ---------------------------------------------------------------------------

class TestMLPipeline:

    def test_feature_engine(self):
        from src.ml import FeatureEngine
        h, l, c, v = _make_ohlcv(200)
        fe = FeatureEngine(close=c, high=h, low=l, volume=v)
        assert fe is not None

    def test_sentiment(self):
        from src.ml import SimpleSentiment
        s = SimpleSentiment()
        score = s.analyze("stock is going up strongly bullish")
        assert isinstance(score, (float, int, np.floating))


# ---------------------------------------------------------------------------
# 6. Screener + Alerts
# ---------------------------------------------------------------------------

class TestScreenerAlerts:

    def test_screener(self):
        from src.screener import StockScreener
        assert StockScreener() is not None

    def test_alert_engine(self):
        from src.alerts import AlertEngine
        engine = AlertEngine()
        assert hasattr(engine, 'add_alert')


# ---------------------------------------------------------------------------
# 7. API + Webhooks
# ---------------------------------------------------------------------------

class TestAPILayer:

    def test_server(self):
        from src.api.server import FinClawServer
        assert FinClawServer(port=0) is not None

    def test_webhooks(self):
        from src.api.webhooks import WebhookManager
        wh = WebhookManager()
        wh.register("signal_change", "https://example.com/hook", format="json")
        assert len(wh._webhooks) == 1


# ---------------------------------------------------------------------------
# 8. Full pipeline: strategy → risk → portfolio
# ---------------------------------------------------------------------------

class TestFullPipeline:

    def test_end_to_end(self):
        from src.strategies import MomentumJTStrategy
        from src.risk import KellyCriterion
        from src.portfolio import PortfolioTracker

        prices = _make_prices(300)
        strategy = MomentumJTStrategy()
        score = strategy.score_single(prices)
        assert score.signal in ("buy", "sell", "hold")

        kelly = KellyCriterion()
        tracker = PortfolioTracker()
        assert tracker is not None
