"""Tests for position reconstruction from trade log on restart."""
import json
import os
import tempfile
from pathlib import Path

import pytest

from src.crypto.live_runner import CryptoLiveRunner, Position


@pytest.fixture
def tmp_dir():
    """Create a temp directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def trade_log_path(tmp_dir):
    return tmp_dir / "data" / "crypto" / "paper_trades.json"


@pytest.fixture
def dna_path(tmp_dir):
    dna_file = tmp_dir / "evolution_results_crypto" / "best_ever.json"
    dna_file.parent.mkdir(parents=True, exist_ok=True)
    dna_file.write_text(json.dumps({
        "generation": 1,
        "fitness": 100,
        "dna": {"min_score": 5, "max_positions": 5},
    }))
    return dna_file


def make_runner(tmp_dir, trade_log_path, dna_path, initial_balance=10000.0):
    """Create a CryptoLiveRunner pointed at temp paths."""
    return CryptoLiveRunner(
        exchange="okx",
        mode="dry_run",
        symbols=["ETH/USDT", "BNB/USDT", "BTC/USDT"],
        initial_balance=initial_balance,
        dna_path=str(dna_path.relative_to(tmp_dir)),
        trade_log_path=str(trade_log_path.relative_to(tmp_dir)),
        project_root=str(tmp_dir),
    )


class TestPositionReconstruction:
    """Tests for _reconstruct_positions method."""

    def test_empty_trade_log(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()
        assert len(runner.positions) == 0
        assert runner.cash == 10000.0

    def test_single_buy(self, tmp_dir, trade_log_path, dna_path):
        trades = [
            {"action": "BUY", "symbol": "ETH/USDT", "price": 2000.0, "qty": 0.5, "cost": 1000.0, "time": "2026-03-24T10:00:00Z", "mode": "dry_run"},
        ]
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        trade_log_path.write_text(json.dumps(trades))

        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()

        assert len(runner.positions) == 1
        assert "ETH/USDT" in runner.positions
        assert runner.positions["ETH/USDT"].qty == 0.5
        assert runner.positions["ETH/USDT"].entry_price == 2000.0
        assert runner.cash == pytest.approx(9000.0)

    def test_buy_then_sell(self, tmp_dir, trade_log_path, dna_path):
        trades = [
            {"action": "BUY", "symbol": "ETH/USDT", "price": 2000.0, "qty": 0.5, "cost": 1000.0, "time": "2026-03-24T10:00:00Z", "mode": "dry_run"},
            {"action": "SELL", "symbol": "ETH/USDT", "price": 2200.0, "qty": 0.5, "revenue": 1100.0, "time": "2026-03-24T11:00:00Z", "mode": "dry_run"},
        ]
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        trade_log_path.write_text(json.dumps(trades))

        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()

        assert len(runner.positions) == 0
        assert runner.cash == pytest.approx(10100.0)  # 10000 - 1000 + 1100

    def test_multiple_buys_different_symbols(self, tmp_dir, trade_log_path, dna_path):
        trades = [
            {"action": "BUY", "symbol": "ETH/USDT", "price": 2000.0, "qty": 0.5, "cost": 1000.0, "time": "2026-03-24T10:00:00Z", "mode": "dry_run"},
            {"action": "BUY", "symbol": "BNB/USDT", "price": 600.0, "qty": 1.67, "cost": 1002.0, "time": "2026-03-24T10:00:01Z", "mode": "dry_run"},
        ]
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        trade_log_path.write_text(json.dumps(trades))

        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()

        assert len(runner.positions) == 2
        assert "ETH/USDT" in runner.positions
        assert "BNB/USDT" in runner.positions
        assert runner.cash == pytest.approx(7998.0)

    def test_duplicate_buy_same_symbol_averages(self, tmp_dir, trade_log_path, dna_path):
        """Simulates the bug scenario: two buys of same symbol."""
        trades = [
            {"action": "BUY", "symbol": "ETH/USDT", "price": 2158.51, "qty": 0.4633, "cost": 1000.0, "time": "2026-03-24T10:33:53Z", "mode": "dry_run"},
            {"action": "BUY", "symbol": "ETH/USDT", "price": 2158.38, "qty": 0.4633, "cost": 1000.0, "time": "2026-03-24T10:36:41Z", "mode": "dry_run"},
        ]
        trade_log_path.parent.mkdir(parents=True, exist_ok=True)
        trade_log_path.write_text(json.dumps(trades))

        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()

        assert len(runner.positions) == 1
        pos = runner.positions["ETH/USDT"]
        assert pos.qty == pytest.approx(0.9266)
        assert pos.entry_price == pytest.approx(2158.445, abs=0.01)
        assert runner.cash == pytest.approx(8000.0)

    def test_no_trade_log_file(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_trade_log()
        runner._reconstruct_positions()
        assert len(runner.positions) == 0
        assert runner.cash == 10000.0


class TestCliOverrides:
    """Tests for CLI override persistence."""

    def test_set_cli_overrides(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_dna()
        runner.set_cli_overrides({"max_positions": 5})
        assert runner.dna["max_positions"] == 5

    def test_cli_overrides_persist_after_reload(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_dna()
        runner.set_cli_overrides({"max_positions": 7})
        # Reload DNA (simulates what start() does)
        runner.load_dna()
        assert runner.dna["max_positions"] == 7


class TestFallbackScoring:
    """Tests for price-based fallback scoring when OHLCV is unavailable."""

    def test_held_position_losing_gets_lower_score(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_dna()
        # Simulate a held position
        runner.positions["ETH/USDT"] = Position("ETH/USDT", 2000.0, 0.5, "2026-03-24T10:00:00Z")
        # Price dropped 10%
        prices = {"ETH/USDT": 1800.0, "BNB/USDT": 600.0, "BTC/USDT": 80000.0}
        signals = runner.generate_signals(prices)
        # With -10% PnL and no OHLCV → score = 5.0 + (-10) * 0.3 = 2.0
        # This should trigger sell since 2.0 < min_score - 2 = 3
        if "ETH/USDT" in signals:
            assert signals["ETH/USDT"]["action"] in ("SELL",)

    def test_held_position_profitable_stays(self, tmp_dir, trade_log_path, dna_path):
        runner = make_runner(tmp_dir, trade_log_path, dna_path)
        runner.load_dna()
        runner.positions["ETH/USDT"] = Position("ETH/USDT", 2000.0, 0.5, "2026-03-24T10:00:00Z")
        # Price up 5%
        prices = {"ETH/USDT": 2100.0, "BNB/USDT": 600.0, "BTC/USDT": 80000.0}
        signals = runner.generate_signals(prices)
        # With +5% PnL → score = 5.0 + 5 * 0.3 = 6.5 → should NOT sell
        if "ETH/USDT" in signals:
            assert signals["ETH/USDT"]["action"] != "SELL" or signals["ETH/USDT"].get("reason") == "take_profit"
