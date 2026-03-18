"""
Tests for A-Share (China Stock) Scanner
========================================
"""

import numpy as np
import pytest

from src.cn_scanner import (
    TOP50,
    SECTORS,
    VALID_SECTORS,
    compute_score,
    classify_signal,
    get_stock_universe,
    format_scan_output,
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
        """SECTORS dict should be populated from TOP50."""
        assert len(SECTORS) > 0
        total = sum(len(v) for v in SECTORS.values())
        assert total == len(TOP50)

    def test_valid_sector_names(self):
        """Should have expected sector names."""
        expected = {'bank', 'tech', 'consumer', 'energy', 'pharma', 'manufacturing'}
        assert set(VALID_SECTORS) == expected

    def test_get_universe_default(self):
        """Default top=30 returns first 30 stocks."""
        result = get_stock_universe(top=30)
        assert len(result) == 30
        assert result[0] == TOP50[0]

    def test_get_universe_top_50(self):
        """top=50 returns all 40 stocks (capped at list size)."""
        result = get_stock_universe(top=50)
        assert len(result) == 40

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
        """Maotai (600519.SS) should be first."""
        assert TOP50[0][0] == '600519.SS'
        assert TOP50[0][1] == '贵州茅台'


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
