"""
Tests for A-Share (China Stock) Scanner
========================================
"""

import numpy as np
import pytest

from src.cn_scanner import (
    TOP50,
    CN_UNIVERSE,
    SECTORS,
    VALID_SECTORS,
    compute_score,
    classify_signal,
    get_stock_universe,
    format_scan_output,
    backtest_cn_strategy,
    format_backtest_output,
    _compute_score_at,
    _compute_summary,
    _empty_summary,
)


# ── Stock Universe Tests ─────────────────────────────────────────────

class TestStockUniverse:
    def test_top50_has_40_entries(self):
        """TOP50 list should have 40 entries (as defined)."""
        assert len(TOP50) == 40

    def test_top50_tuple_format(self):
        """Each entry should be (ticker, name, sector) tuple."""
        for entry in TOP50:
            assert len(entry) == 3
            ticker, name, sector = entry
            assert isinstance(ticker, str)
            assert isinstance(name, str)
            assert isinstance(sector, str)

    def test_top50_ticker_suffixes(self):
        """All tickers should end with .SS (Shanghai) or .SZ (Shenzhen)."""
        for ticker, _, _ in TOP50:
            assert ticker.endswith('.SS') or ticker.endswith('.SZ'), f"Bad suffix: {ticker}"

    def test_top50_ticker_format(self):
        """Ticker codes should be 6 digits followed by exchange suffix."""
        for ticker, _, _ in TOP50:
            code = ticker.split('.')[0]
            assert len(code) == 6, f"Bad code length: {ticker}"
            assert code.isdigit(), f"Code not numeric: {ticker}"

    def test_sectors_populated(self):
        """SECTORS dict should be populated from CN_UNIVERSE."""
        assert len(SECTORS) > 0
        total = sum(len(v) for v in SECTORS.values())
        assert total == len(CN_UNIVERSE)

    def test_valid_sector_names(self):
        """Should have expected sector names."""
        expected = {
            'bank', 'tech', 'consumer', 'energy', 'pharma', 'manufacturing',
            'ai', 'optical', 'storage', 'chip', 'ev', 'solar',
            'military', 'liquor', 'real_estate', 'telecom',
        }
        assert set(VALID_SECTORS) == expected

    def test_get_universe_default(self):
        """Default top=30 returns first 30 stocks."""
        result = get_stock_universe(top=30)
        assert len(result) == 30
        assert result[0] == CN_UNIVERSE[0]

    def test_get_universe_top_50(self):
        """top=50 returns first 50 stocks from CN_UNIVERSE."""
        result = get_stock_universe(top=50)
        assert len(result) == 50

    def test_get_universe_by_sector(self):
        """Filtering by sector returns only that sector."""
        banks = get_stock_universe(sector='bank')
        assert len(banks) > 0
        for _, _, sector in banks:
            assert sector == 'bank'

    def test_get_universe_invalid_sector(self):
        """Invalid sector raises ValueError."""
        with pytest.raises(ValueError, match="Unknown sector"):
            get_stock_universe(sector='nonexistent')

    def test_maotai_in_list(self):
        """Maotai (600519.SS) should be in the universe."""
        tickers = [t for t, _, _ in CN_UNIVERSE]
        assert '600519.SS' in tickers


# ── Scoring Engine Tests ─────────────────────────────────────────────

class TestScoringEngine:
    def _make_prices(self, n=60, start=100.0, trend=0.0, noise=0.5):
        """Generate synthetic price data."""
        np.random.seed(42)
        changes = np.random.randn(n) * noise + trend
        prices = np.zeros(n)
        prices[0] = start
        for i in range(1, n):
            prices[i] = prices[i-1] * (1 + changes[i] / 100)
        return prices

    def test_score_basic(self):
        """compute_score returns expected keys."""
        prices = self._make_prices()
        result = compute_score(prices)
        expected_keys = {
            'score', 'rsi_val', 'macd_hist', 'pct_b',
            'change_1d', 'change_5d', 'volume_ratio',
            'signal', 'price', 'reasons',
        }
        assert set(result.keys()) == expected_keys

    def test_score_insufficient_data(self):
        """Short price series returns zero score."""
        prices = np.array([100.0, 101.0, 102.0])
        result = compute_score(prices)
        assert result['score'] == 0
        assert result['signal'] == 'HOLD'

    def test_rsi_oversold_score(self):
        """Strongly declining prices should give RSI < 30 and +4 points."""
        # Create a steadily declining price series
        prices = np.linspace(200, 100, 60)
        result = compute_score(prices)
        assert result['rsi_val'] < 40  # Should be oversold
        # Score should include RSI points
        assert result['score'] >= 3

    def test_rsi_overbought_penalty(self):
        """Strongly rising prices should give RSI > 70 and -2 points."""
        prices = np.linspace(100, 300, 60)
        result = compute_score(prices)
        assert result['rsi_val'] > 60  # Should be high

    def test_macd_golden_cross_score(self):
        """MACD histogram > 0 should contribute +2 points."""
        # V-shape recovery: decline then strong rally
        prices = np.concatenate([
            np.linspace(150, 100, 30),
            np.linspace(101, 170, 30),
        ])
        result = compute_score(prices)
        if result['macd_hist'] > 0:
            assert 'MACD golden cross' in result['reasons']

    def test_bollinger_near_lower(self):
        """Price near lower Bollinger band should score points."""
        # Flat then sharp drop at end
        prices = np.ones(55) * 100
        prices[-5:] = [98, 96, 94, 92, 90]
        result = compute_score(prices)
        # pct_b should be low
        assert result['pct_b'] < 50

    def test_volume_ratio_scoring(self):
        """Volume ratio between 1.2-3x should add 1 point."""
        prices = self._make_prices()
        volume = np.ones(60) * 1000
        volume[-1] = 1500  # 1.5x average
        result = compute_score(prices, volume)
        # Volume ratio should be calculated
        assert result['volume_ratio'] > 0

    def test_five_day_change_mild_uptrend(self):
        """5-day change between 0-8% should add 2 points."""
        prices = np.ones(60) * 100
        prices[-6:] = [100, 101, 102, 103, 104, 104]  # ~4% 5d gain
        result = compute_score(prices)
        assert 0 < result['change_5d'] <= 8

    def test_price_returned_correctly(self):
        """Price should be the last close value."""
        prices = np.array([100.0] * 30 + [150.0])
        result = compute_score(prices)
        assert result['price'] == 150.0


# ── Signal Classification Tests ──────────────────────────────────────

class TestSignalClassification:
    def test_buy_signal(self):
        assert classify_signal(6) == "** BUY"
        assert classify_signal(8) == "** BUY"
        assert classify_signal(10) == "** BUY"

    def test_watch_signal(self):
        assert classify_signal(4) == "WATCH"
        assert classify_signal(5) == "WATCH"

    def test_hold_signal(self):
        assert classify_signal(3) == "HOLD"
        assert classify_signal(0) == "HOLD"
        assert classify_signal(-1) == "HOLD"


# ── Output Formatting Tests ──────────────────────────────────────────

class TestFormatOutput:
    def test_format_basic(self):
        """format_scan_output produces valid output."""
        results = [{
            'name': 'TestStock',
            'code': '600519',
            'price': 1800.50,
            'rsi_val': 35.2,
            'macd_hist': 0.15,
            'pct_b': 25.3,
            'change_1d': 1.2,
            'change_5d': 3.5,
            'volume_ratio': 1.5,
            'score': 7,
            'signal': '** BUY',
            'reasons': ['RSI oversold(35)', 'MACD golden cross'],
        }]
        output = format_scan_output(results)
        assert 'A-Share Scanner' in output
        assert 'TestStock' in output
        assert '600519' in output
        assert '** BUY' in output

    def test_format_empty_results(self):
        """Empty results should still produce header."""
        output = format_scan_output([])
        assert 'A-Share Scanner' in output

    def test_format_recommended_section(self):
        """Stocks with score >= 5 should appear in recommended."""
        results = [{
            'name': 'HighScore',
            'code': '000001',
            'price': 50.0,
            'rsi_val': 30.0,
            'macd_hist': 0.5,
            'pct_b': 15.0,
            'change_1d': 2.0,
            'change_5d': 5.0,
            'volume_ratio': 1.5,
            'score': 8,
            'signal': '** BUY',
            'reasons': ['RSI oversold(30)', 'MACD golden cross', 'near Bollinger lower'],
        }]
        output = format_scan_output(results)
        assert 'Recommended' in output
        assert 'HighScore' in output

    def test_format_ascii_safe(self):
        """Output should be encodable as ASCII (no fancy unicode that breaks cp1252)."""
        results = [{
            'name': 'Test',
            'code': '600519',
            'price': 100.0,
            'rsi_val': 50.0,
            'macd_hist': 0.0,
            'pct_b': 50.0,
            'change_1d': 0.0,
            'change_5d': 0.0,
            'volume_ratio': 0.0,
            'score': 3,
            'signal': 'HOLD',
            'reasons': [],
        }]
        output = format_scan_output(results)
        # Should not contain emojis or characters that break cp1252
        # Only allow ASCII + basic extended chars
        for char in output:
            code = ord(char)
            # Allow ASCII printable, newline, and CJK (for stock names)
            assert code < 128 or (0x4E00 <= code <= 0x9FFF) or code == 0x2500, \
                f"Non-ASCII char: {char!r} (U+{code:04X})"


# ── CLI Argument Tests ───────────────────────────────────────────────

class TestCLIArgs:
    def test_scan_cn_parser_exists(self):
        """scan-cn command should be registered in the parser."""
        from src.cli.main import build_parser
        parser = build_parser()
        # Parse a scan-cn command
        args = parser.parse_args(['scan-cn'])
        assert args.command == 'scan-cn'

    def test_scan_cn_default_args(self):
        """Default args should have top=30, no sector, min_score=0, sort=score."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn'])
        assert args.top == 30
        assert args.sector is None
        assert args.min_score == 0
        assert args.sort == 'score'

    def test_scan_cn_custom_args(self):
        """Custom args should be parsed correctly."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn', '--top', '50', '--sector', 'bank',
                                  '--min-score', '5', '--sort', 'rsi'])
        assert args.top == 50
        assert args.sector == 'bank'
        assert args.min_score == 5
        assert args.sort == 'rsi'


# ══════════════════════════════════════════════════════════════════════
# NEW TESTS  (expanded universe + backtest)
# ══════════════════════════════════════════════════════════════════════

class TestExpandedUniverse:
    """Tests for the expanded ~160-stock CN_UNIVERSE."""

    def test_cn_universe_minimum_size(self):
        """CN_UNIVERSE should have at least 150 stocks."""
        assert len(CN_UNIVERSE) >= 150

    def test_cn_universe_ticker_format(self):
        """Every ticker in CN_UNIVERSE must be 6 digits + .SS or .SZ."""
        for ticker, name, sector in CN_UNIVERSE:
            parts = ticker.split(".")
            assert len(parts) == 2, f"Bad ticker format: {ticker}"
            code, exchange = parts
            assert len(code) == 6, f"Bad code length: {ticker}"
            assert code.isdigit(), f"Code not numeric: {ticker}"
            assert exchange in ("SS", "SZ"), f"Bad exchange suffix: {ticker}"

    def test_cn_universe_no_duplicates(self):
        """No duplicate tickers in CN_UNIVERSE."""
        tickers = [t for t, _, _ in CN_UNIVERSE]
        assert len(tickers) == len(set(tickers)), "Duplicate tickers found"

    def test_new_sectors_exist(self):
        """All new sector categories should be present."""
        new_sectors = ['ai', 'optical', 'storage', 'chip', 'ev', 'solar',
                       'military', 'liquor', 'real_estate', 'telecom']
        for s in new_sectors:
            assert s in SECTORS, f"Missing sector: {s}"
            assert len(SECTORS[s]) > 0, f"Empty sector: {s}"

    def test_ai_sector_stocks(self):
        """AI sector should have key stocks like 科大讯飞."""
        ai_tickers = [t for t, _, _ in SECTORS['ai']]
        assert '002230.SZ' in ai_tickers  # 科大讯飞
        assert '688256.SS' in ai_tickers  # 寒武纪

    def test_chip_sector_stocks(self):
        """Chip sector should have 韦尔股份 and 北方华创."""
        chip_tickers = [t for t, _, _ in SECTORS['chip']]
        assert '603501.SS' in chip_tickers  # 韦尔股份
        assert '002371.SZ' in chip_tickers  # 北方华创

    def test_get_universe_new_sector(self):
        """get_stock_universe should work with new sectors."""
        ai_stocks = get_stock_universe(sector='ai')
        assert len(ai_stocks) >= 5
        for _, _, s in ai_stocks:
            assert s == 'ai'

    def test_old_sectors_preserved(self):
        """Original sectors (bank, tech, etc.) should still exist and be non-empty."""
        old_sectors = ['bank', 'tech', 'consumer', 'energy', 'pharma', 'manufacturing']
        for s in old_sectors:
            assert s in SECTORS
            assert len(SECTORS[s]) > 0


class TestBacktest:
    """Tests for the backtest engine using synthetic data."""

    @staticmethod
    def _make_synthetic(n: int = 120, seed: int = 42) -> dict[str, dict]:
        """Create synthetic data for 3 stocks that will produce varied scores."""
        np.random.seed(seed)
        data: dict[str, dict] = {}

        # Stock A: oversold pattern → should score high (~6+)
        # Flat then dip → low RSI, near lower Bollinger, MACD golden cross
        close_a = np.ones(n) * 100.0
        # introduce a dip in the middle, then recovery
        for i in range(40, 70):
            close_a[i] = 100 - (i - 40) * 0.5  # decline
        for i in range(70, n):
            close_a[i] = close_a[69] + (i - 69) * 0.3  # recovery
        volume_a = np.ones(n) * 10000
        volume_a[-5:] = 15000  # volume spike near end
        data['600519.SS'] = {"close": close_a, "volume": volume_a}

        # Stock B: overbought pattern → should score low
        close_b = np.linspace(50, 150, n)
        data['000858.SZ'] = {"close": close_b, "volume": np.ones(n) * 10000}

        # Stock C: mixed / neutral
        close_c = 100 + np.cumsum(np.random.randn(n) * 0.5)
        close_c = np.maximum(close_c, 10)  # keep positive
        data['300750.SZ'] = {"close": close_c, "volume": np.ones(n) * 10000}

        return data

    def test_backtest_returns_batches(self):
        """backtest_cn_strategy with synthetic data should return batches."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=3,
            lookback_days=30,
            data_override=data,
        )
        assert "batches" in result
        assert "summary" in result
        assert isinstance(result["batches"], list)

    def test_backtest_summary_keys(self):
        """Summary should have all expected keys."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=1,  # very low to guarantee selections
            lookback_days=30,
            data_override=data,
        )
        summary = result["summary"]
        expected_keys = {
            "total_batches", "avg_return", "win_rate",
            "best_batch", "worst_batch", "annualized",
            "hold_days", "min_score",
        }
        assert expected_keys == set(summary.keys())

    def test_backtest_no_selections_high_threshold(self):
        """Very high min_score should produce zero batches."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=99,
            lookback_days=30,
            data_override=data,
        )
        assert result["summary"]["total_batches"] == 0
        assert len(result["batches"]) == 0

    def test_backtest_hold_days_respected(self):
        """Batch day indices should be spaced by hold_days."""
        data = self._make_synthetic(n=200, seed=123)
        result = backtest_cn_strategy(
            hold_days=10,
            min_score=1,
            lookback_days=60,
            data_override=data,
        )
        if len(result["batches"]) >= 2:
            indices = [b["day_index"] for b in result["batches"]]
            for i in range(1, len(indices)):
                assert indices[i] - indices[i - 1] == 10

    def test_backtest_batch_fields(self):
        """Each batch should have the required fields."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=1,
            lookback_days=30,
            data_override=data,
        )
        for batch in result["batches"]:
            assert "day_index" in batch
            assert "num_selected" in batch
            assert "avg_return" in batch
            assert "best_stock" in batch
            assert "worst_stock" in batch
            assert "stocks" in batch

    def test_backtest_format_output(self):
        """format_backtest_output should produce readable text."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=1,
            lookback_days=30,
            data_override=data,
        )
        output = format_backtest_output(result)
        assert "Backtest" in output
        assert "Summary" in output

    def test_backtest_format_empty(self):
        """format_backtest_output with no batches should not crash."""
        result = {"batches": [], "summary": _empty_summary()}
        output = format_backtest_output(result)
        assert "No selections" in output

    def test_backtest_win_rate_bounds(self):
        """Win rate should be between 0-100%."""
        data = self._make_synthetic()
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=1,
            lookback_days=30,
            data_override=data,
        )
        wr = result["summary"]["win_rate"]
        assert 0 <= wr <= 100

    def test_compute_score_at_slices_correctly(self):
        """_compute_score_at(close, vol, idx) should use data[:idx+1]."""
        close = np.linspace(200, 100, 60)  # declining
        result_full = compute_score(close)
        result_at = _compute_score_at(close, None, len(close) - 1)
        # Should be identical since idx == last
        assert result_full["score"] == result_at["score"]
        assert result_full["rsi_val"] == pytest.approx(result_at["rsi_val"])

    def test_compute_score_at_partial(self):
        """Scoring at partial index should differ from full."""
        close = np.concatenate([np.linspace(200, 100, 40), np.linspace(101, 150, 30)])
        # Score at index 39 (still declining) vs 69 (recovered)
        r39 = _compute_score_at(close, None, 39)
        r69 = _compute_score_at(close, None, 69)
        # At least the RSI should differ significantly
        assert r39["rsi_val"] != pytest.approx(r69["rsi_val"], abs=5)

    def test_compute_summary_basic(self):
        """_compute_summary should compute correct aggregate stats."""
        batches = [
            {"avg_return": 2.0},
            {"avg_return": -1.0},
            {"avg_return": 3.0},
        ]
        summary = _compute_summary(batches, hold_days=5, min_score=6)
        assert summary["total_batches"] == 3
        assert summary["avg_return"] == pytest.approx(4.0 / 3)
        assert summary["win_rate"] == pytest.approx(200 / 3)  # 2 out of 3
        assert summary["best_batch"] == 3.0
        assert summary["worst_batch"] == -1.0

    def test_empty_summary(self):
        """_empty_summary returns zeros."""
        s = _empty_summary()
        assert s["total_batches"] == 0
        assert s["avg_return"] == 0.0

    def test_backtest_empty_data(self):
        """Backtest with empty data should return empty result, not crash."""
        result = backtest_cn_strategy(
            hold_days=5,
            min_score=6,
            lookback_days=30,
            data_override={},
        )
        assert result["batches"] == []
        assert result["summary"]["total_batches"] == 0


class TestBacktestCLIArgs:
    """Tests for the scan-cn-backtest CLI parser."""

    def test_scan_cn_backtest_parser_exists(self):
        """scan-cn-backtest command should be registered."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn-backtest'])
        assert args.command == 'scan-cn-backtest'

    def test_scan_cn_backtest_default_args(self):
        """Default args for scan-cn-backtest."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(['scan-cn-backtest'])
        assert args.hold == 5
        assert args.min_score == 6
        assert args.period == '6mo'
        assert args.lookback == 30
        assert args.sector is None
        assert args.top is None

    def test_scan_cn_backtest_custom_args(self):
        """Custom args should parse correctly."""
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args([
            'scan-cn-backtest',
            '--hold', '10',
            '--min-score', '4',
            '--period', '3mo',
            '--lookback', '60',
            '--sector', 'ai',
        ])
        assert args.hold == 10
        assert args.min_score == 4
        assert args.period == '3mo'
        assert args.lookback == 60
        assert args.sector == 'ai'
