"""
Multi-Strategy Ensemble - Let strategies vote
==============================================
Instead of relying on one strategy, combine all strategies' signals.
A stock must be recommended by multiple strategies to get a buy signal.

This is how ai-hedge-fund works: 17 agents vote, consensus wins.

5 strategies vote:
  1. CN Scanner v3  - Technical indicator composite (RSI + MACD + BB + volume)
  2. Trend Discovery - R² trend clarity + slope + RSI oversold rebound
  3. Golden Dip      - Bull stock pullback buy (R² bull + dip + volume shrink)
  4. Imminent Breakout - Donchian channel breakout + volume surge
  5. Limit-Up Pullback - 涨停回调不破底 (limit-up day → pullback → buy)

Each strategy independently scores 0-10.  Score >= 7 is a "buy" vote.
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EnsembleSignal:
    """Result of multi-strategy voting for one stock."""
    code: str
    name: str
    price: float
    votes: int              # how many strategies recommend (score >= 7)
    total_strategies: int   # out of how many (always 5)
    consensus: float        # votes / total (0.0-1.0)
    strategies: List[str]   # which strategies voted buy
    scores: Dict[str, float] = field(default_factory=dict)  # strategy→score
    avg_score: float = 0.0  # average score across ALL strategies
    signal: str = "skip"    # "strong_buy" / "buy" / "watch" / "skip"


# ─── Pure numpy indicator helpers ────────────────────────────────────

def _sma(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average. Returns array of same length (leading NaNs)."""
    out = np.full(len(arr), np.nan)
    if len(arr) < window:
        return out
    cs = np.cumsum(arr)
    out[window - 1:] = (cs[window - 1:] - np.concatenate([[0], cs[:-window]])) / window
    return out


def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average."""
    out = np.full(len(arr), np.nan)
    if len(arr) < period:
        return out
    k = 2.0 / (period + 1)
    out[period - 1] = np.mean(arr[:period])
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out


def _rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI (Wilder's smoothing). Returns array of same length (leading NaNs)."""
    prices = np.asarray(prices, dtype=np.float64)
    n = len(prices)
    rsi_out = np.full(n, np.nan)
    if n < period + 1:
        return rsi_out
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        rsi_out[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi_out[period] = 100.0 - 100.0 / (1.0 + rs)
    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi_out[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_out[i + 1] = 100.0 - 100.0 / (1.0 + rs)
    return rsi_out


def _macd(prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, histogram."""
    ema_fast = _ema(prices, fast)
    ema_slow = _ema(prices, slow)
    macd_line = ema_fast - ema_slow
    # signal line is EMA of macd_line starting from first valid
    valid_start = slow - 1
    sig_line = np.full(len(prices), np.nan)
    if len(prices) >= valid_start + signal:
        k = 2.0 / (signal + 1)
        sig_line[valid_start + signal - 1] = np.nanmean(macd_line[valid_start:valid_start + signal])
        for i in range(valid_start + signal, len(prices)):
            if not np.isnan(macd_line[i]) and not np.isnan(sig_line[i - 1]):
                sig_line[i] = macd_line[i] * k + sig_line[i - 1] * (1 - k)
    hist = macd_line - sig_line
    return macd_line, sig_line, hist


def _bollinger_pct_b(prices: np.ndarray, period: int = 20, std_mult: float = 2.0) -> float:
    """Bollinger %B for last bar. Returns 0-1 range (can exceed)."""
    if len(prices) < period:
        return 0.5
    window = prices[-period:]
    mid = np.mean(window)
    std = np.std(window, ddof=0)
    if std == 0:
        return 0.5
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    band_width = upper - lower
    if band_width == 0:
        return 0.5
    return (prices[-1] - lower) / band_width


def _r2(prices: np.ndarray, window: int) -> float:
    """R-squared over the last *window* bars."""
    if len(prices) < window or window < 2:
        return 0.0
    y = prices[-window:].astype(np.float64)
    x = np.arange(window, dtype=np.float64)
    y_mean = np.mean(y)
    ss_tot = np.sum((y - y_mean) ** 2)
    if ss_tot == 0:
        return 0.0
    x_mean = np.mean(x)
    slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
    y_pred = slope * x + (y_mean - slope * x_mean)
    ss_res = np.sum((y - y_pred) ** 2)
    return max(0.0, 1.0 - ss_res / ss_tot)


def _slope_norm(prices: np.ndarray, window: int) -> float:
    """Normalised slope (daily fractional change implied by linear fit)."""
    if len(prices) < window or window < 2:
        return 0.0
    y = prices[-window:].astype(np.float64)
    x = np.arange(window, dtype=np.float64)
    x_mean, y_mean = np.mean(x), np.mean(y)
    denom = np.sum((x - x_mean) ** 2)
    if denom == 0 or y_mean == 0:
        return 0.0
    slope = np.sum((x - x_mean) * (y - y_mean)) / denom
    return slope / y_mean


def _adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """ADX value (last bar). Returns 0 if insufficient data."""
    n = len(closes)
    if n < period + 1:
        return 0.0
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm_list.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm_list.append(down_move if down_move > up_move and down_move > 0 else 0.0)
    if len(tr_list) < period:
        return 0.0
    atr = np.mean(tr_list[:period])
    plus_dm_avg = np.mean(plus_dm_list[:period])
    minus_dm_avg = np.mean(minus_dm_list[:period])
    dx_list = []
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        plus_dm_avg = (plus_dm_avg * (period - 1) + plus_dm_list[i]) / period
        minus_dm_avg = (minus_dm_avg * (period - 1) + minus_dm_list[i]) / period
        if atr == 0:
            continue
        plus_di = 100 * plus_dm_avg / atr
        minus_di = 100 * minus_dm_avg / atr
        di_sum = plus_di + minus_di
        if di_sum == 0:
            continue
        dx_list.append(abs(plus_di - minus_di) / di_sum * 100)
    if len(dx_list) < period:
        return np.mean(dx_list) if dx_list else 0.0
    adx_val = np.mean(dx_list[:period])
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period
    return adx_val


# ─── Strategy scoring functions ──────────────────────────────────────

class StrategyEnsemble:
    """Combine 5 strategies into consensus signals via voting."""

    STRATEGY_NAMES = [
        "cn_scanner",
        "trend_discovery",
        "golden_dip",
        "imminent_breakout",
        "limit_up_pullback",
    ]

    def __init__(self, min_votes: int = 2, min_consensus: float = 0.4):
        """
        Args:
            min_votes: minimum strategies that must agree for a buy signal
            min_consensus: minimum agreement ratio (0.0-1.0)
        """
        self.min_votes = min_votes
        self.min_consensus = min_consensus

    # ─── 1. CN Scanner v3 scoring ────────────────────────────

    def score_cn_scanner(
        self,
        closes: np.ndarray,
        volumes: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
    ) -> float:
        """Score using cn_scanner v3 logic. Returns 0-10.

        Simplified v3 scoring:
          - RSI oversold (<30 → +2, <40 → +1.5, <50 → +0.5)
          - MACD histogram positive → +1.5
          - Bollinger %B < 0.2 → +2, < 0.4 → +1
          - 5-day change 0-8% → +1
          - Volume ratio 1.2-3.0 → +0.5
          - ADX > 25 → +1
          - Three soldiers pattern → +1.5
        Max ~10.
        """
        closes = np.asarray(closes, dtype=np.float64)
        if len(closes) < 30:
            return 0.0

        score = 0.0

        # RSI
        rsi_arr = _rsi(closes, 14)
        rsi_val = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0
        if rsi_val < 30:
            score += 2.0
        elif rsi_val < 40:
            score += 1.5
        elif rsi_val < 50:
            score += 0.5

        # MACD histogram
        _, _, hist = _macd(closes)
        macd_hist = float(hist[-1]) if not np.isnan(hist[-1]) else 0.0
        if macd_hist > 0:
            score += 1.5

        # Bollinger %B
        pct_b = _bollinger_pct_b(closes)
        if pct_b < 0.2:
            score += 2.0
        elif pct_b < 0.4:
            score += 1.0

        # 5-day change
        if len(closes) >= 6:
            change_5d = (closes[-1] / closes[-6] - 1) * 100
            if 0 < change_5d <= 8:
                score += 1.0

        # Volume ratio
        if volumes is not None and len(volumes) >= 21:
            vol = np.asarray(volumes, dtype=np.float64)
            avg_vol = np.mean(vol[-21:-1])
            if avg_vol > 0:
                vr = vol[-1] / avg_vol
                if 1.2 <= vr <= 3.0:
                    score += 0.5

        # ADX trend strength
        if highs is not None and lows is not None and len(closes) >= 30:
            adx_val = _adx(
                np.asarray(highs, dtype=np.float64),
                np.asarray(lows, dtype=np.float64),
                closes,
            )
            if adx_val > 25:
                score += 1.0

        # Three soldiers (simplified): 3 consecutive bullish candles with increasing close
        if opens is not None and len(closes) >= 3:
            o = np.asarray(opens, dtype=np.float64)
            last3_bull = all(closes[-3 + i] > o[-3 + i] for i in range(3))
            last3_rising = closes[-3] < closes[-2] < closes[-1]
            if last3_bull and last3_rising:
                score += 1.5

        return min(10.0, score)

    # ─── 2. Trend Discovery scoring ─────────────────────────

    def score_trend_discovery(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Score using trend discovery logic. Returns 0-10.

        Scoring (maps TrendDiscovery 0-100 → 0-10):
          - RSI was oversold (<20 in last 60d): +2.5
          - R²(60d) > 0.5: +2.0; > 0.3: +1.0
          - R² increasing (30d > 60d or 60d > 120d): +1.5
          - Positive slope(30d): +1.5
          - 60d return > 30%: +1.5; > 10%: +0.8
          - Volume trending up (10d avg / 30d avg > 1.1): +1.0
        Max = 10.
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        if n < 30:
            return 0.0

        score = 0.0

        # RSI min in last 60 days
        rsi_arr = _rsi(closes, 14)
        lookback = min(60, n)
        rsi_tail = rsi_arr[-lookback:]
        valid_rsi = rsi_tail[~np.isnan(rsi_tail)]
        rsi_min = float(np.min(valid_rsi)) if len(valid_rsi) > 0 else 50.0
        if rsi_min < 20:
            score += 2.5

        # R² at multiple windows
        r2_30 = _r2(closes, min(30, n))
        r2_60 = _r2(closes, min(60, n))
        r2_120 = _r2(closes, min(120, n))

        if r2_60 > 0.5:
            score += 2.0
        elif r2_60 > 0.3:
            score += 1.0

        # R² increasing
        if r2_30 > r2_60 or (r2_60 > r2_120 and r2_120 > 0):
            score += 1.5

        # Positive slope
        slope = _slope_norm(closes, min(30, n))
        if slope > 0:
            score += 1.5

        # 60d return
        ret_window = min(60, n - 1)
        if ret_window > 0:
            ret_60 = (closes[-1] / closes[-(ret_window + 1)] - 1) * 100
            if ret_60 > 30:
                score += 1.5
            elif ret_60 > 10:
                score += 0.8

        # Volume trending up
        if volumes is not None and len(volumes) >= 30:
            vols = np.asarray(volumes, dtype=np.float64)
            vol_recent = np.mean(vols[-10:])
            vol_older = np.mean(vols[-30:-10])
            if vol_older > 0 and vol_recent / vol_older > 1.1:
                score += 1.0

        return min(10.0, score)

    # ─── 3. Golden Dip scoring ──────────────────────────────

    def score_golden_dip(self, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Score using golden dip logic. Returns 0-10.

        Simplified golden dip scoring:
          - Is bull stock? (R²(120d) > 0.6, positive slope, 60d return > 20%): prerequisite
          - Pullback >= 10% from recent 60d high: +3.0
          - RSI < 35: +3.0
          - R²(120d) still > 0.5 during dip: +2.0
          - Volume shrinkage (5d avg / 20d avg < 0.7): +2.0
        Max = 10.  Returns 0 if not a bull stock.
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        if n < 120:
            return 0.0

        # Must be a bull stock first
        r2_120 = _r2(closes, 120)
        slope_120 = _slope_norm(closes, 120)
        ret_60 = (closes[-1] / closes[-61] - 1) if n >= 61 else 0.0

        if r2_120 < 0.6 or slope_120 <= 0 or ret_60 < 0.20:
            return 0.0

        score = 0.0

        # Pullback from 60d high
        lookback = min(60, n)
        recent_high = np.max(closes[-lookback:])
        pullback = (recent_high - closes[-1]) / recent_high if recent_high > 0 else 0.0
        if pullback >= 0.10:
            score += 3.0
            if pullback >= 0.15:
                score += 0.5

        # RSI < 35
        rsi_arr = _rsi(closes, 14)
        current_rsi = float(rsi_arr[-1]) if not np.isnan(rsi_arr[-1]) else 50.0
        if current_rsi < 35:
            score += 3.0
            if current_rsi < 25:
                score += 0.5

        # R² still decent
        if r2_120 >= 0.5:
            score += 2.0

        # Volume shrinkage
        if volumes is not None and len(volumes) >= 20:
            vols = np.asarray(volumes, dtype=np.float64)
            vol_recent = np.mean(vols[-5:]) if np.mean(vols[-5:]) > 0 else 1.0
            vol_avg = np.mean(vols[-20:]) if np.mean(vols[-20:]) > 0 else 1.0
            if vol_recent / vol_avg < 0.7:
                score += 2.0

        return min(10.0, score)

    # ─── 4. Imminent Breakout scoring ───────────────────────

    def score_imminent_breakout(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
    ) -> float:
        """Score using Donchian breakout + volume logic. Returns 0-10.

        Simplified breakout scoring:
          - Price above 20d Donchian upper channel: +3.0
          - Volume > 1.5x 20d average: +2.5
          - ADX > 25 (trending): +1.5
          - Close > Open (bullish candle): +1.0
          - 5-day momentum positive: +1.0
          - Squeeze release (BB width expanding after narrow): +1.0
        Max = 10.
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        if n < 21:
            return 0.0

        score = 0.0

        # Donchian upper channel (20-day high of highs)
        h = np.asarray(highs, dtype=np.float64) if highs is not None else closes
        l = np.asarray(lows, dtype=np.float64) if lows is not None else closes
        upper_20 = np.max(h[-21:-1])  # 20d high (excluding today)
        if closes[-1] > upper_20:
            score += 3.0

        # Volume surge
        if volumes is not None and len(volumes) >= 21:
            vols = np.asarray(volumes, dtype=np.float64)
            avg_vol = np.mean(vols[-21:-1])
            if avg_vol > 0 and vols[-1] / avg_vol >= 1.5:
                score += 2.5

        # ADX
        if len(closes) >= 30:
            adx_val = _adx(h, l, closes)
            if adx_val > 25:
                score += 1.5

        # Bullish candle
        if opens is not None:
            o = np.asarray(opens, dtype=np.float64)
            if closes[-1] > o[-1]:
                score += 1.0

        # 5-day momentum
        if n >= 6 and closes[-1] > closes[-6]:
            score += 1.0

        # Squeeze release: BB width expanding
        if n >= 20:
            std_now = np.std(closes[-20:])
            std_prev = np.std(closes[-40:-20]) if n >= 40 else np.std(closes[:20])
            if std_prev > 0 and std_now / std_prev > 1.5:
                score += 1.0

        return min(10.0, score)

    # ─── 5. Limit-Up Pullback scoring ──────────────────────

    def score_limit_up_pullback(
        self,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
    ) -> float:
        """Score using limit-up pullback logic. Returns 0-10.

        Checks for a recent limit-up day followed by pullback:
          - Limit-up day in last 5 days (close/prev_close >= 1.095): +3.0
          - Pullback didn't break limit-up day's low: +2.0
          - Volume shrinkage during pullback (< 60%): +2.5
          - Pullback is pulling back (close < limit-up close): +1.5
          - 2-3 day pullback (ideal timing): +1.0
        Max = 10.
        """
        closes = np.asarray(closes, dtype=np.float64)
        n = len(closes)
        if n < 7:
            return 0.0

        opens = np.asarray(opens, dtype=np.float64) if opens is not None else closes.copy()
        highs = np.asarray(highs, dtype=np.float64) if highs is not None else closes.copy()
        lows = np.asarray(lows, dtype=np.float64) if lows is not None else closes.copy()
        volumes = np.asarray(volumes, dtype=np.float64) if volumes is not None else np.ones(n)

        score = 0.0
        best_score = 0.0

        # Look for limit-up in last 5 trading days
        for lookback in range(2, min(6, n)):
            lu_idx = n - 1 - lookback
            if lu_idx < 1:
                continue

            # Check if that day was a limit-up
            change = closes[lu_idx] / closes[lu_idx - 1]
            if change < 1.095:
                continue

            # Found a limit-up day
            candidate_score = 3.0

            lu_low = lows[lu_idx]
            lu_vol = volumes[lu_idx]
            pb_days = n - 1 - lu_idx  # days since limit-up

            # Check pullback didn't break limit-up low
            pullback_lows = lows[lu_idx + 1:]
            if len(pullback_lows) > 0 and np.all(pullback_lows >= lu_low):
                candidate_score += 2.0

            # Volume shrinkage
            if lu_vol > 0 and len(volumes[lu_idx + 1:]) > 0:
                avg_pb_vol = np.mean(volumes[lu_idx + 1:])
                if avg_pb_vol / lu_vol < 0.6:
                    candidate_score += 2.5

            # Currently pulling back (close < limit-up close)
            if closes[-1] < closes[lu_idx]:
                candidate_score += 1.5

            # Ideal pullback length (2-3 days)
            if 2 <= pb_days <= 3:
                candidate_score += 1.0

            best_score = max(best_score, candidate_score)

        return min(10.0, best_score)

    # ─── Core: Evaluate one stock ───────────────────────────

    def evaluate_stock(
        self,
        dates: np.ndarray,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
        name: str = "",
    ) -> EnsembleSignal:
        """Run all 5 strategies on one stock, count votes.

        Each strategy scores 0-10:
          - Score >= 7: counts as a "buy" vote
          - Score >= 5: "watch" (doesn't count as vote)
          - Score < 5: skip

        Signal classification:
          - votes >= 3 or consensus >= 0.6: "strong_buy"
          - votes >= 2 or consensus >= 0.4: "buy"
          - votes == 1: "watch"
          - votes == 0: "skip"
        """
        closes = np.asarray(closes, dtype=np.float64)
        opens = np.asarray(opens, dtype=np.float64) if opens is not None else closes.copy()
        highs = np.asarray(highs, dtype=np.float64) if highs is not None else closes.copy()
        lows = np.asarray(lows, dtype=np.float64) if lows is not None else closes.copy()
        volumes = np.asarray(volumes, dtype=np.float64) if volumes is not None else np.ones(len(closes))

        price = float(closes[-1]) if len(closes) > 0 else 0.0

        # Run all 5 strategies
        scores = {
            "cn_scanner": self.score_cn_scanner(closes, volumes, opens, highs, lows),
            "trend_discovery": self.score_trend_discovery(closes, volumes),
            "golden_dip": self.score_golden_dip(closes, volumes),
            "imminent_breakout": self.score_imminent_breakout(opens, highs, lows, closes, volumes),
            "limit_up_pullback": self.score_limit_up_pullback(opens, highs, lows, closes, volumes),
        }

        # Count votes (score >= 7 = buy vote)
        voting_strategies = [name for name, s in scores.items() if s >= 7.0]
        votes = len(voting_strategies)
        total = len(self.STRATEGY_NAMES)
        consensus = votes / total if total > 0 else 0.0
        avg_score = sum(scores.values()) / total if total > 0 else 0.0

        # Classify signal
        if votes >= 3 or consensus >= 0.6:
            signal = "strong_buy"
        elif votes >= 2 or consensus >= 0.4:
            signal = "buy"
        elif votes >= 1:
            signal = "watch"
        else:
            signal = "skip"

        return EnsembleSignal(
            code=code,
            name=name,
            price=price,
            votes=votes,
            total_strategies=total,
            consensus=consensus,
            strategies=voting_strategies,
            scores=scores,
            avg_score=avg_score,
            signal=signal,
        )

    # ─── Batch scan ─────────────────────────────────────────

    def scan_all(self, stock_data: dict) -> List[EnsembleSignal]:
        """Scan all stocks, return ranked by votes then avg_score.

        Args:
            stock_data: {code: {"dates": arr, "opens": arr, "highs": arr,
                                "lows": arr, "closes": arr, "volumes": arr,
                                "name": str}}

        Returns:
            List of EnsembleSignal sorted by (votes desc, avg_score desc),
            excluding "skip" signals.
        """
        results = []
        for code, data in stock_data.items():
            dates = data.get("dates", np.array([]))
            opens = data.get("opens")
            highs = data.get("highs")
            lows = data.get("lows")
            closes = data.get("closes", np.array([]))
            volumes = data.get("volumes")
            name = data.get("name", "")

            if len(closes) < 30:
                continue

            sig = self.evaluate_stock(
                dates, opens, highs, lows, closes, volumes,
                code=code, name=name,
            )
            if sig.signal != "skip":
                results.append(sig)

        results.sort(key=lambda s: (s.votes, s.avg_score), reverse=True)
        return results

    # ─── Daily signal report ────────────────────────────────

    def generate_daily_signal(
        self,
        stock_data: dict,
        max_positions: int = 2,
        capital: float = 1_000_000,
    ) -> str:
        """Generate human-readable daily trading signal.

        Args:
            stock_data: same format as scan_all()
            max_positions: max number of buy recommendations
            capital: total capital for position sizing

        Returns:
            Formatted signal report string.
        """
        signals = self.scan_all(stock_data)
        today = datetime.now().strftime("%Y-%m-%d")
        per_position = capital / max_positions if max_positions > 0 else capital

        lines = [
            f"📊 {today} 交易信号",
            f"{'=' * 40}",
            "",
        ]

        # Buy signals
        buy_signals = [s for s in signals if s.signal in ("strong_buy", "buy")]
        if buy_signals:
            lines.append("🟢 买入：")
            for i, sig in enumerate(buy_signals[:max_positions], 1):
                stars = "★" * sig.votes + "☆" * (sig.total_strategies - sig.votes)
                shares = int(per_position / sig.price / 100) * 100 if sig.price > 0 else 0
                lines.append(
                    f"  {i}. {sig.code} {sig.name} ¥{sig.price:.2f} "
                    f"({sig.votes}/{sig.total_strategies}策略推荐) {stars}"
                )
                lines.append(f"     策略: {', '.join(sig.strategies)}")
                lines.append(f"     建议: {shares}股 ≈ ¥{shares * sig.price:,.0f}")
        else:
            lines.append("🟢 买入：无合适标的")

        lines.append("")

        # Watch signals
        watch_signals = [s for s in signals if s.signal == "watch"]
        if watch_signals:
            lines.append("👀 关注：")
            for sig in watch_signals[:5]:
                lines.append(
                    f"  - {sig.code} {sig.name} ¥{sig.price:.2f} "
                    f"(得分: {sig.avg_score:.1f})"
                )
        else:
            lines.append("👀 关注：无")

        lines.append("")
        lines.append(f"⚙️ 共扫描 {len(stock_data)} 只股票")
        lines.append(f"  买入信号: {len(buy_signals)} 只")
        lines.append(f"  关注: {len(watch_signals)} 只")

        return "\n".join(lines)
