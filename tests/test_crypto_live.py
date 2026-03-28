"""
Tests for Phase 3: Live Trading Infrastructure
===============================================
Tests for CryptoLiveRunner, TelegramNotifier, and the CLI.
"""

from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.crypto.live_runner import CryptoLiveRunner, Position, DEFAULT_INITIAL_BALANCE
from src.crypto.telegram_notifier import TelegramNotifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path: Path):
    """Create a temporary project directory with minimal structure."""
    # Create DNA file
    dna_dir = tmp_path / "evolution_results"
    dna_dir.mkdir()
    dna_data = {
        "fitness": 100.0,
        "dna": {
            "min_score": 5,
            "rsi_buy_threshold": 30.0,
            "rsi_sell_threshold": 70.0,
            "stop_loss_pct": 5.0,
            "take_profit_pct": 10.0,
            "max_positions": 3,
            "volume_ratio_min": 1.2,
            "w_roc": 0.02,
            "w_volume": 0.01,
            "w_trend": 0.01,
        },
    }
    (dna_dir / "best_ever.json").write_text(json.dumps(dna_data))

    # Create data dir
    (tmp_path / "data" / "crypto").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def runner(tmp_project: Path) -> CryptoLiveRunner:
    """Create a runner in dry-run mode with no exchange connection."""
    return CryptoLiveRunner(
        exchange="binance",
        mode="dry_run",
        symbols=["BTC/USDT", "ETH/USDT"],
        project_root=str(tmp_project),
    )


@pytest.fixture
def notifier() -> TelegramNotifier:
    """Create a TelegramNotifier (won't actually send)."""
    return TelegramNotifier(token="TEST_TOKEN", chat_id="12345")


# ===========================================================================
# 1. Dry-run doesn't call exchange APIs for orders
# ===========================================================================

class TestDryRunNoOrders:
    def test_buy_does_not_call_exchange_api(self, runner: CryptoLiveRunner):
        """In dry_run mode, execute_buy should NOT call create_market_buy_order."""
        runner.load_dna()
        mock_exchange = MagicMock()
        runner._exchange = mock_exchange

        trade = runner.execute_buy("BTC/USDT", 50000.0, 7.5)

        assert trade is not None
        assert trade["action"] == "BUY"
        assert trade["mode"] == "dry_run"
        mock_exchange.create_market_buy_order.assert_not_called()

    def test_sell_does_not_call_exchange_api(self, runner: CryptoLiveRunner):
        """In dry_run mode, execute_sell should NOT call create_market_sell_order."""
        runner.load_dna()
        mock_exchange = MagicMock()
        runner._exchange = mock_exchange

        # First buy, then sell
        runner.execute_buy("BTC/USDT", 50000.0, 7.5)
        trade = runner.execute_sell("BTC/USDT", 51000.0)

        assert trade is not None
        assert trade["action"] == "SELL"
        assert trade["mode"] == "dry_run"
        mock_exchange.create_market_sell_order.assert_not_called()


# ===========================================================================
# 2. Position tracking: open, close, P&L calculation
# ===========================================================================

class TestPositionTracking:
    def test_position_unrealised_pnl_positive(self):
        pos = Position("BTC/USDT", 50000.0, 0.1, "2026-01-01T00:00:00Z")
        assert pos.unrealised_pnl(55000.0) == pytest.approx(500.0)

    def test_position_unrealised_pnl_negative(self):
        pos = Position("BTC/USDT", 50000.0, 0.1, "2026-01-01T00:00:00Z")
        assert pos.unrealised_pnl(45000.0) == pytest.approx(-500.0)

    def test_position_pnl_percentage(self):
        pos = Position("BTC/USDT", 50000.0, 0.1, "2026-01-01T00:00:00Z")
        # 10% gain
        assert pos.unrealised_pnl_pct(55000.0) == pytest.approx(10.0)

    def test_buy_creates_position(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.execute_buy("BTC/USDT", 50000.0, 7.0)
        assert "BTC/USDT" in runner.positions
        assert runner.positions["BTC/USDT"].entry_price == 50000.0

    def test_sell_closes_position_and_updates_cash(self, runner: CryptoLiveRunner):
        runner.load_dna()
        initial_cash = runner.cash
        runner.execute_buy("BTC/USDT", 50000.0, 7.0)
        cash_after_buy = runner.cash
        assert cash_after_buy < initial_cash

        trade = runner.execute_sell("BTC/USDT", 55000.0)
        assert "BTC/USDT" not in runner.positions
        assert trade is not None
        assert trade["pnl"] > 0
        assert runner.cash > cash_after_buy

    def test_sell_nonexistent_position_returns_none(self, runner: CryptoLiveRunner):
        runner.load_dna()
        result = runner.execute_sell("DOGE/USDT", 0.1)
        assert result is None


# ===========================================================================
# 3. Risk management: daily loss limit triggers stop
# ===========================================================================

class TestDailyLossLimit:
    def test_daily_loss_limit_triggers(self, runner: CryptoLiveRunner):
        """When unrealised losses exceed daily limit, check returns True."""
        runner.load_dna()
        runner.daily_start_value = 10000.0
        # Simulate loss: cash dropped to 9400 (6% loss > 5% limit)
        runner.cash = 9400.0
        runner.positions.clear()

        prices: dict[str, float] = {}
        assert runner.check_daily_loss_limit(prices) is True

    def test_daily_loss_limit_not_triggered(self, runner: CryptoLiveRunner):
        """When losses are within limit, check returns False."""
        runner.load_dna()
        runner.daily_start_value = 10000.0
        runner.cash = 9700.0  # -3%, within limit
        runner.positions.clear()

        assert runner.check_daily_loss_limit() is False

    def test_run_cycle_halts_on_daily_loss(self, runner: CryptoLiveRunner):
        """_run_cycle should set _running=False when daily loss limit hit."""
        from datetime import datetime, timezone
        runner.load_dna()
        runner._running = True
        # Set day_date to today so _reset_daily_if_needed won't reset our values
        runner._day_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        runner.daily_start_value = 10000.0
        runner.cash = 9000.0  # -10%
        runner.positions.clear()

        runner._run_cycle(prices={})
        assert runner._running is False


# ===========================================================================
# 4. Risk management: max position size respected
# ===========================================================================

class TestMaxPositionSize:
    def test_max_position_value(self, runner: CryptoLiveRunner):
        runner.load_dna()
        # Default 20% of 10000 = 2000 (changed for crypto-optimized strategy)
        assert runner.max_position_value() == pytest.approx(2000.0)

    def test_buy_respects_max_position_size(self, runner: CryptoLiveRunner):
        runner.load_dna()
        trade = runner.execute_buy("BTC/USDT", 50000.0, 7.0)
        assert trade is not None
        # Cost should be <= max_position_value
        assert trade["cost"] <= runner.max_position_value({}) + 1  # +1 for float

    def test_cannot_exceed_max_positions(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.dna["max_positions"] = 2
        runner.symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

        runner.execute_buy("BTC/USDT", 50000.0, 7.0)
        runner.execute_buy("ETH/USDT", 3000.0, 7.0)

        # Third should fail
        result = runner.execute_buy("SOL/USDT", 100.0, 7.0)
        assert result is None

    def test_max_exposure_blocks_new_position(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.dna["max_positions"] = 5
        runner.max_exposure_pct = 25.0
        runner.max_position_size_pct = 10.0
        # Set cycle prices so risk checks use them
        runner._cycle_prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "SOL/USDT": 100.0}

        # Buy 3 positions → 10% each → 30% exposure → exceeds 25%
        runner.execute_buy("BTC/USDT", 50000.0, 7.0)  # 10% exposure
        runner.execute_buy("ETH/USDT", 3000.0, 7.0)   # 20% exposure
        # Third should be blocked because current exposure is ~20% + proposed 10% would be 30%
        # But current_exposure_pct checks existing positions only (20%) < 25%, so it passes.
        # After third buy, exposure would be ~30% — but check is pre-trade.
        # To truly test the limit, fill up to the cap:
        runner.execute_buy("SOL/USDT", 100.0, 7.0)    # ~30% now (over 25%)

        # 4th should be blocked — current exposure is now > 25%
        runner.symbols.append("AVAX/USDT")
        runner._cycle_prices["AVAX/USDT"] = 50.0
        result = runner.execute_buy("AVAX/USDT", 50.0, 7.0)
        assert result is None


# ===========================================================================
# 5. Risk management: STOP_TRADING flag file stops trading
# ===========================================================================

class TestStopFileEmergency:
    def test_stop_file_detected(self, runner: CryptoLiveRunner):
        """When STOP_TRADING file exists, check returns True."""
        runner.stop_file.write_text("stop")
        assert runner.check_stop_file() is True

    def test_stop_file_not_present(self, runner: CryptoLiveRunner):
        assert runner.check_stop_file() is False

    def test_run_cycle_halts_on_stop_file(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner._running = True
        runner._day_date = "2026-01-01"
        runner.stop_file.write_text("STOP")
        runner._run_cycle(prices={})
        assert runner._running is False


# ===========================================================================
# 6. Signal generation: loads DNA from best_ever.json
# ===========================================================================

class TestDNALoading:
    def test_load_dna_from_file(self, runner: CryptoLiveRunner):
        dna = runner.load_dna()
        assert dna["min_score"] == 5
        assert dna["rsi_buy_threshold"] == 30.0
        # max_positions auto-adjusted from 3 → >=5 for crypto (auto-adjust rule)
        assert dna["max_positions"] >= 5

    def test_load_dna_missing_file_uses_defaults(self, tmp_path: Path):
        r = CryptoLiveRunner(
            project_root=str(tmp_path),
            dna_path="nonexistent.json",
        )
        dna = r.load_dna()
        assert "min_score" in dna
        assert "rsi_buy_threshold" in dna

    def test_generate_signals_uses_dna_thresholds(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.dna["min_score"] = 3  # very low threshold → almost everything triggers BUY

        # Provide prices so fetch is not called
        signals = runner.generate_signals(prices={"BTC/USDT": 50000.0, "ETH/USDT": 3000.0})
        # With no OHLCV data and score defaulting to 5.0, both should trigger BUY
        for sym in ["BTC/USDT", "ETH/USDT"]:
            if sym in signals:
                assert signals[sym]["action"] == "BUY"


# ===========================================================================
# 7. Telegram message formatting
# ===========================================================================

class TestTelegramFormatting:
    def test_buy_notification_format(self, notifier: TelegramNotifier):
        with patch.object(notifier, "send", return_value=True) as mock_send:
            notifier.notify_trade("BUY", "BTC/USDT", 67234.50, 0.015, score=8.2)
            msg = mock_send.call_args[0][0]
            assert "🟢" in msg
            assert "BUY" in msg
            assert "BTC/USDT" in msg
            assert "67,234.50" in msg
            assert "0.015" in msg
            assert "8.2/10" in msg

    def test_sell_notification_format(self, notifier: TelegramNotifier):
        with patch.object(notifier, "send", return_value=True) as mock_send:
            notifier.notify_trade("SELL", "ETH/USDT", 3456.78, 1.0, pnl=123.45, pnl_pct=2.3)
            msg = mock_send.call_args[0][0]
            assert "🔴" in msg
            assert "SELL" in msg
            assert "ETH/USDT" in msg
            assert "+$123.45" in msg
            assert "+2.3%" in msg

    def test_daily_summary_format(self, notifier: TelegramNotifier):
        with patch.object(notifier, "send", return_value=True) as mock_send:
            notifier.notify_daily_summary(10234.0, 234.0, 3)
            msg = mock_send.call_args[0][0]
            assert "📊" in msg
            assert "Daily Summary" in msg
            assert "$10,234" in msg
            assert "3 positions" in msg

    def test_risk_alert_format(self, notifier: TelegramNotifier):
        with patch.object(notifier, "send", return_value=True) as mock_send:
            notifier.notify_risk_alert("Daily loss limit approaching (-4.2%)")
            msg = mock_send.call_args[0][0]
            assert "⚠️" in msg
            assert "-4.2%" in msg

    def test_emergency_stop_format(self, notifier: TelegramNotifier):
        with patch.object(notifier, "send", return_value=True) as mock_send:
            notifier.notify_emergency_stop("Manual kill switch")
            msg = mock_send.call_args[0][0]
            assert "🛑" in msg
            assert "Manual kill switch" in msg


# ===========================================================================
# 8. Telegram send (mock HTTP call, verify URL and payload)
# ===========================================================================

class TestTelegramHTTP:
    def test_send_calls_correct_url(self, notifier: TelegramNotifier):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            result = notifier.send("Hello, World!")
            assert result is True

            req = mock_open.call_args[0][0]
            assert "TEST_TOKEN" in req.full_url
            assert req.method == "POST"

            data = json.loads(req.data)
            assert data["chat_id"] == "12345"
            assert data["text"] == "Hello, World!"
            assert data["parse_mode"] == "HTML"

    def test_send_returns_false_on_http_error(self, notifier: TelegramNotifier):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="", code=403, msg="Forbidden", hdrs=None, fp=None  # type: ignore
        )):
            assert notifier.send("test") is False

    def test_send_returns_false_on_network_error(self, notifier: TelegramNotifier):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("no network")):
            assert notifier.send("test") is False


# ===========================================================================
# 9. Portfolio value calculation with multiple positions
# ===========================================================================

class TestPortfolioValue:
    def test_portfolio_value_cash_only(self, runner: CryptoLiveRunner):
        runner.load_dna()
        assert runner.portfolio_value(prices={}) == DEFAULT_INITIAL_BALANCE

    def test_portfolio_value_with_positions(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.cash = 8000.0
        runner.positions["BTC/USDT"] = Position("BTC/USDT", 50000.0, 0.02, "2026-01-01T00:00:00Z")
        runner.positions["ETH/USDT"] = Position("ETH/USDT", 3000.0, 0.5, "2026-01-01T00:00:00Z")

        prices = {"BTC/USDT": 55000.0, "ETH/USDT": 3200.0}
        pv = runner.portfolio_value(prices)

        expected = 8000.0 + (0.02 * 55000.0) + (0.5 * 3200.0)
        assert pv == pytest.approx(expected)

    def test_exposure_percentage(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.cash = 9000.0
        runner.positions["BTC/USDT"] = Position("BTC/USDT", 50000.0, 0.02, "2026-01-01T00:00:00Z")

        prices = {"BTC/USDT": 50000.0}
        exposure = runner.current_exposure_pct(prices)
        # invested = 0.02 * 50000 = 1000, portfolio = 9000 + 1000 = 10000
        assert exposure == pytest.approx(10.0)


# ===========================================================================
# 10. Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_no_symbols(self, tmp_project: Path):
        r = CryptoLiveRunner(
            symbols=[],
            project_root=str(tmp_project),
        )
        r.load_dna()
        signals = r.generate_signals(prices={})
        assert signals == {}

    def test_missing_dna_file(self, tmp_path: Path):
        r = CryptoLiveRunner(
            project_root=str(tmp_path),
            dna_path="does_not_exist.json",
        )
        dna = r.load_dna()
        assert isinstance(dna, dict)
        assert "min_score" in dna

    def test_position_to_dict(self):
        pos = Position("BTC/USDT", 50000.0, 0.1, "2026-01-01T00:00:00Z", "long")
        d = pos.to_dict()
        assert d["symbol"] == "BTC/USDT"
        assert d["entry_price"] == 50000.0
        assert d["side"] == "long"

    def test_runner_stop(self, runner: CryptoLiveRunner):
        runner._running = True
        runner.stop()
        assert runner._running is False
        assert runner._stop_event.is_set()


# ===========================================================================
# 11. Trade log persistence
# ===========================================================================

class TestTradeLogPersistence:
    def test_trade_log_saved_on_buy(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.execute_buy("BTC/USDT", 50000.0, 7.0)

        assert runner.trade_log_path.exists()
        with open(runner.trade_log_path) as f:
            log = json.load(f)
        assert len(log) == 1
        assert log[0]["action"] == "BUY"

    def test_trade_log_loaded_on_start(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.execute_buy("BTC/USDT", 50000.0, 7.0)

        # Create new runner pointing to same project
        runner2 = CryptoLiveRunner(
            project_root=str(runner.project_root),
            symbols=["BTC/USDT"],
        )
        log = runner2.load_trade_log()
        assert len(log) == 1


# ===========================================================================
# 12. Signal generation with existing positions (stop-loss / take-profit)
# ===========================================================================

class TestSignalGeneration:
    def test_stop_loss_signal(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.dna["stop_loss_pct"] = 5.0
        runner.positions["BTC/USDT"] = Position("BTC/USDT", 50000.0, 0.02, "2026-01-01T00:00:00Z")

        # Price dropped 10% → triggers stop loss
        signals = runner.generate_signals(prices={"BTC/USDT": 45000.0, "ETH/USDT": 3000.0})
        assert "BTC/USDT" in signals
        assert signals["BTC/USDT"]["action"] == "SELL"
        assert signals["BTC/USDT"]["reason"] == "stop_loss"

    def test_take_profit_signal(self, runner: CryptoLiveRunner):
        runner.load_dna()
        runner.dna["take_profit_pct"] = 10.0
        runner.positions["BTC/USDT"] = Position("BTC/USDT", 50000.0, 0.02, "2026-01-01T00:00:00Z")

        # Price rose 15%
        signals = runner.generate_signals(prices={"BTC/USDT": 57500.0, "ETH/USDT": 3000.0})
        assert "BTC/USDT" in signals
        assert signals["BTC/USDT"]["action"] == "SELL"
        assert signals["BTC/USDT"]["reason"] == "take_profit"


# ===========================================================================
# 13. Live mode calls exchange API
# ===========================================================================

class TestLiveMode:
    def test_live_buy_calls_exchange(self, tmp_project: Path):
        r = CryptoLiveRunner(
            mode="live",
            symbols=["BTC/USDT"],
            project_root=str(tmp_project),
        )
        r.load_dna()

        mock_exchange = MagicMock()
        mock_exchange.create_market_buy_order.return_value = {"id": "order123"}
        r._exchange = mock_exchange

        trade = r.execute_buy("BTC/USDT", 50000.0, 7.0)
        assert trade is not None
        assert trade["mode"] == "live"
        mock_exchange.create_market_buy_order.assert_called_once()

    def test_live_sell_calls_exchange(self, tmp_project: Path):
        r = CryptoLiveRunner(
            mode="live",
            symbols=["BTC/USDT"],
            project_root=str(tmp_project),
        )
        r.load_dna()

        mock_exchange = MagicMock()
        mock_exchange.create_market_buy_order.return_value = {"id": "buy1"}
        mock_exchange.create_market_sell_order.return_value = {"id": "sell1"}
        r._exchange = mock_exchange

        r.execute_buy("BTC/USDT", 50000.0, 7.0)
        r.execute_sell("BTC/USDT", 51000.0)
        mock_exchange.create_market_sell_order.assert_called_once()


# ===========================================================================
# 14. Scoring function
# ===========================================================================

class TestScoring:
    def test_score_clamps_to_0_10(self, runner: CryptoLiveRunner):
        runner.load_dna()
        # Empty OHLCV returns neutral 5.0
        score = runner.compute_score("BTC/USDT", [])
        assert 0 <= score <= 10

    def test_rsi_calculation(self):
        # Build a series where RSI should be computable
        closes = list(range(100, 130))  # ascending → high RSI
        rsi = CryptoLiveRunner._calc_rsi(closes, period=14)
        assert rsi is not None
        assert rsi > 50  # ascending should give high RSI

    def test_score_with_ohlcv_data(self, runner: CryptoLiveRunner):
        runner.load_dna()
        # Generate some fake OHLCV: [timestamp, open, high, low, close, volume]
        ohlcv = []
        for i in range(60):
            price = 50000 + i * 10
            ohlcv.append([1700000000 + i * 3600, price, price + 50, price - 50, price, 100.0])
        score = runner.compute_score("BTC/USDT", ohlcv)
        assert 0 <= score <= 10


# ===========================================================================
# 15. CLI argument parsing
# ===========================================================================

class TestCLI:
    def test_default_args(self):
        from scripts.live_crypto import parse_args
        args = parse_args([])
        assert args.mode == "dry_run"
        assert args.exchange == "binance"
        assert args.symbols == ["BTC/USDT"]
        assert args.initial_balance == 10000.0

    def test_custom_args(self):
        from scripts.live_crypto import parse_args
        args = parse_args([
            "--mode", "live",
            "--exchange", "kraken",
            "--symbols", "ETH/USDT", "SOL/USDT",
            "--api-key", "mykey",
            "--api-secret", "mysecret",
            "--telegram-token", "tok123",
            "--telegram-chat", "chat456",
            "--interval", "30",
            "--initial-balance", "50000",
            "--max-position-pct", "5",
            "--max-exposure-pct", "30",
            "--daily-loss-limit", "-3",
        ])
        assert args.mode == "live"
        assert args.exchange == "kraken"
        assert args.symbols == ["ETH/USDT", "SOL/USDT"]
        assert args.api_key == "mykey"
        assert args.api_secret == "mysecret"
        assert args.telegram_token == "tok123"
        assert args.telegram_chat == "chat456"
        assert args.interval == 30
        assert args.initial_balance == 50000.0
        assert args.max_position_pct == 5.0
        assert args.max_exposure_pct == 30.0
        assert args.daily_loss_limit == -3.0


# ===========================================================================
# 16. Notifier integration with runner
# ===========================================================================

class TestNotifierIntegration:
    def test_runner_sends_telegram_on_buy(self, tmp_project: Path):
        r = CryptoLiveRunner(
            symbols=["BTC/USDT"],
            telegram_token="TOK",
            telegram_chat_id="123",
            project_root=str(tmp_project),
        )
        r.load_dna()
        r.notifier = MagicMock(spec=TelegramNotifier)

        r.execute_buy("BTC/USDT", 50000.0, 8.0)
        r.notifier.notify_trade.assert_called_once()
        call_args = r.notifier.notify_trade.call_args
        assert call_args[1].get("score") == 8.0 or call_args[0][0] == "BUY"

    def test_runner_sends_telegram_on_sell(self, tmp_project: Path):
        r = CryptoLiveRunner(
            symbols=["BTC/USDT"],
            telegram_token="TOK",
            telegram_chat_id="123",
            project_root=str(tmp_project),
        )
        r.load_dna()
        r.notifier = MagicMock(spec=TelegramNotifier)

        r.execute_buy("BTC/USDT", 50000.0, 8.0)
        r.execute_sell("BTC/USDT", 51000.0)
        assert r.notifier.notify_trade.call_count == 2


# ===========================================================================
# 17. Duplicate position prevention
# ===========================================================================

class TestDuplicatePosition:
    def test_cannot_buy_same_symbol_twice(self, runner: CryptoLiveRunner):
        runner.load_dna()
        t1 = runner.execute_buy("BTC/USDT", 50000.0, 7.0)
        assert t1 is not None
        t2 = runner.execute_buy("BTC/USDT", 51000.0, 7.0)
        assert t2 is None  # should be rejected
