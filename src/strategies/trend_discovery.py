"""
Trend Discovery Strategy - Find the next 10x stock
====================================================
Inspired by 源杰科技 (688498): 91元 → 1115元 in 1 year.

Key insight: Great trend stocks don't start with volume breakouts.
They start with:
1. Extreme RSI oversold (<15)
2. R² gradually increasing (trend forming)
3. Positive slope (price going up)
4. Buy and hold, NOT short-term trading

This strategy runs PARALLEL to cn_scanner's short-term signals.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class TrendCandidate:
    """A stock evaluated for long-term trend potential."""

    code: str
    name: str
    price: float
    score: float  # 0-100
    rsi_min_60d: float  # Minimum RSI in last 60 days
    r2_30d: float  # Recent trend clarity (R²)
    r2_60d: float
    r2_120d: float
    slope_30d: float  # Trend direction (normalised daily return implied by fit)
    total_return_60d: float  # 60-day total return in %
    signal: str  # "emerging_trend" / "strong_trend" / "mature_trend" / "no_trend"
    hold_suggestion: str  # "buy_and_hold" / "watch" / "take_profit"


class TrendDiscovery:
    """Find stocks with emerging strong trends for long-term holding.

    Scoring dimensions (max 100 points):
      - RSI was recently oversold (<threshold):  +25
      - R² 60d > 0.5 (trend forming):           +20
      - R² increasing (acceleration):           +15
      - Positive slope:                          +15
      - 60d return > 30%:                        +15
      - Volume trending up:                      +10
    """

    def __init__(
        self,
        rsi_oversold_threshold: float = 20.0,
        r2_emerging_min: float = 0.4,
        r2_strong_min: float = 0.7,
        slope_min: float = 0.0,
        min_return_60d: float = 10.0,
    ):
        self.rsi_oversold_threshold = rsi_oversold_threshold
        self.r2_emerging_min = r2_emerging_min
        self.r2_strong_min = r2_strong_min
        self.slope_min = slope_min
        self.min_return_60d = min_return_60d

    # ─── indicator helpers (pure NumPy) ──────────────────────

    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI series.  Returns array of same length (leading NaNs)."""
        prices = np.asarray(prices, dtype=np.float64)
        n = len(prices)
        rsi = np.full(n, np.nan)
        if n < period + 1:
            return rsi

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            rsi[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[period] = 100.0 - 100.0 / (1.0 + rs)

        for i in range(period, n - 1):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)

        return rsi

    @staticmethod
    def calculate_r2(prices: np.ndarray, window: int) -> float:
        """R-squared (trend linearity) over the last *window* bars.

        Returns 0.0 when there is insufficient data or zero variance.
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < window or window < 2:
            return 0.0
        y = prices[-window:]
        x = np.arange(window, dtype=np.float64)
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        if ss_tot == 0:
            return 0.0
        # least-squares slope & intercept
        x_mean = np.mean(x)
        slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
        intercept = y_mean - slope * x_mean
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        r2 = 1.0 - ss_res / ss_tot
        return max(r2, 0.0)

    @staticmethod
    def calculate_slope(prices: np.ndarray, window: int) -> float:
        """Normalised slope (daily return implied by linear fit) over *window* bars.

        A value of 0.01 means the linear fit implies +1 % per day.
        Returns 0.0 when data is insufficient.
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < window or window < 2:
            return 0.0
        y = prices[-window:]
        x = np.arange(window, dtype=np.float64)
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        denom = np.sum((x - x_mean) ** 2)
        if denom == 0:
            return 0.0
        slope = np.sum((x - x_mean) * (y - y_mean)) / denom
        # normalise: slope / mean price → daily fractional change
        if y_mean == 0:
            return 0.0
        return slope / y_mean

    # ─── core analysis ───────────────────────────────────────

    def analyze_stock(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        code: str = "",
        name: str = "",
    ) -> TrendCandidate:
        """Analyze a single stock for trend potential."""
        prices = np.asarray(prices, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64) if volumes is not None else np.zeros(len(prices))
        n = len(prices)

        # Guard: need at least 30 bars for any meaningful analysis
        if n < 30:
            return TrendCandidate(
                code=code, name=name,
                price=float(prices[-1]) if n > 0 else 0.0,
                score=0.0,
                rsi_min_60d=50.0,
                r2_30d=0.0, r2_60d=0.0, r2_120d=0.0,
                slope_30d=0.0, total_return_60d=0.0,
                signal="no_trend", hold_suggestion="watch",
            )

        # RSI
        rsi_series = self.calculate_rsi(prices, 14)
        lookback_60 = min(60, n)
        rsi_tail = rsi_series[-lookback_60:]
        valid_rsi = rsi_tail[~np.isnan(rsi_tail)]
        rsi_min_60d = float(np.min(valid_rsi)) if len(valid_rsi) > 0 else 50.0
        current_rsi = float(valid_rsi[-1]) if len(valid_rsi) > 0 else 50.0

        # R² at multiple windows
        r2_30d = self.calculate_r2(prices, min(30, n))
        r2_60d = self.calculate_r2(prices, min(60, n))
        r2_120d = self.calculate_r2(prices, min(120, n))

        # Slope
        slope_30d = self.calculate_slope(prices, min(30, n))

        # Total return over last 60 days
        ret_window = min(60, n - 1)
        total_return_60d = (prices[-1] / prices[-(ret_window + 1)] - 1) * 100 if ret_window > 0 else 0.0

        # ── Scoring (max 100) ──
        score = 0.0

        # 1. RSI oversold recently (+25)
        if rsi_min_60d < self.rsi_oversold_threshold:
            score += 25.0

        # 2. R² 60d > 0.5 → trend forming (+20)
        if r2_60d > 0.5:
            score += 20.0
        elif r2_60d > 0.3:
            score += 10.0

        # 3. R² increasing (+15)
        r2_increasing = False
        if r2_30d > r2_60d or (r2_60d > r2_120d and r2_120d > 0):
            score += 15.0
            r2_increasing = True

        # 4. Positive slope (+15)
        if slope_30d > self.slope_min:
            score += 15.0

        # 5. 60d return (+15)
        if total_return_60d > 30:
            score += 15.0
        elif total_return_60d > self.min_return_60d:
            score += 8.0

        # 6. Volume trending up (+10)
        if len(volumes) >= 30 and np.mean(volumes[-10:]) > 0:
            vol_recent = np.mean(volumes[-10:])
            vol_older = np.mean(volumes[-30:-10])
            if vol_older > 0 and vol_recent / vol_older > 1.1:
                score += 10.0

        # ── Signal classification ──
        if score >= 70 and r2_60d >= self.r2_strong_min and current_rsi > 80:
            signal = "mature_trend"
            hold_suggestion = "take_profit"
        elif score >= 70 and r2_60d >= self.r2_strong_min:
            signal = "strong_trend"
            hold_suggestion = "buy_and_hold"
        elif score >= 50 and r2_60d >= self.r2_emerging_min:
            signal = "emerging_trend"
            hold_suggestion = "watch"
        else:
            signal = "no_trend"
            hold_suggestion = "watch"

        return TrendCandidate(
            code=code,
            name=name,
            price=float(prices[-1]),
            score=score,
            rsi_min_60d=rsi_min_60d,
            r2_30d=r2_30d,
            r2_60d=r2_60d,
            r2_120d=r2_120d,
            slope_30d=slope_30d,
            total_return_60d=total_return_60d,
            signal=signal,
            hold_suggestion=hold_suggestion,
        )

    # ─── batch scan ──────────────────────────────────────────

    def scan(self, stock_data: dict[str, dict]) -> list[TrendCandidate]:
        """Scan multiple stocks for trend candidates.

        Args:
            stock_data: ``{code: {"prices": np.array, "volumes": np.array, "name": str}}``

        Returns:
            List of :class:`TrendCandidate` sorted by score (highest first),
            excluding ``"no_trend"`` results.
        """
        candidates: list[TrendCandidate] = []
        for code, data in stock_data.items():
            prices = data.get("prices", np.array([]))
            volumes = data.get("volumes", None)
            name = data.get("name", "")
            tc = self.analyze_stock(prices, volumes, code=code, name=name)
            if tc.signal != "no_trend":
                candidates.append(tc)
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    # ─── sell / exit logic ───────────────────────────────────

    def should_sell(self, prices: np.ndarray) -> tuple[bool, str]:
        """Check if a held trend position should be sold.

        Conservative sell conditions:
          - R² drops below 0.3  (trend breaking down)
          - RSI > 85            (extremely overbought)
          - Slope negative for last 10 bars
          - 20 % drawdown from recent high

        Returns:
            ``(should_sell, reason)``
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < 15:
            return False, "insufficient_data"

        # 1. 20 % drawdown from recent high (most critical — check first)
        recent_high = np.max(prices[-60:]) if len(prices) >= 60 else np.max(prices)
        if recent_high > 0:
            dd = (prices[-1] - recent_high) / recent_high
            if dd < -0.20:
                return True, "drawdown_20pct"

        # 2. R² breakdown
        r2 = self.calculate_r2(prices, min(30, len(prices)))
        if r2 < 0.3:
            return True, "r2_breakdown"

        # 3. Overbought RSI
        rsi = self.calculate_rsi(prices, 14)
        valid = rsi[~np.isnan(rsi)]
        if len(valid) > 0 and valid[-1] > 85:
            return True, "rsi_overbought"

        # 4. Negative slope sustained (10-day)
        if len(prices) >= 10:
            slope_10 = self.calculate_slope(prices, 10)
            if slope_10 < 0:
                return True, "slope_negative"

        return False, ""

    # ─── reporting ───────────────────────────────────────────

    @staticmethod
    def generate_report(candidates: list[TrendCandidate]) -> str:
        """Generate a readable report of trend candidates."""
        if not candidates:
            return "No trend candidates found."

        lines = [
            "=" * 70,
            "  Trend Discovery Report",
            "=" * 70,
            "",
            f"  {'Code':<10} {'Name':<10} {'Price':>8} {'Score':>6} "
            f"{'R²30':>6} {'R²60':>6} {'R²120':>6} {'Slope':>8} {'Ret60':>8} {'Signal':<16} {'Suggestion'}",
            "-" * 110,
        ]
        for c in candidates:
            lines.append(
                f"  {c.code:<10} {c.name:<10} {c.price:>8.2f} {c.score:>5.0f} "
                f"{c.r2_30d:>6.3f} {c.r2_60d:>6.3f} {c.r2_120d:>6.3f} "
                f"{c.slope_30d:>+7.4f} {c.total_return_60d:>+7.1f}% "
                f"{c.signal:<16} {c.hold_suggestion}"
            )
        lines.append("")
        lines.append(f"  Total candidates: {len(candidates)}")
        lines.append("=" * 70)
        return "\n".join(lines)
