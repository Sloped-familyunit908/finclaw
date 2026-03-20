"""
Golden Dip Buy Strategy - 黄金坑买入
======================================
Core idea: Confirm bull stock → wait for pullback dip → buy the fear → hold against human nature.

Inspired by 源杰科技 (688498): 91元 → 1115元 (+1117%), with many dips along the way.
Each dip was a "golden dip" — a buying opportunity in a strong trend.

Strategy logic:
  Step 1: Confirm bull stock (120d R² > 0.6, positive slope, 60d return > 20%)
  Step 2: Detect golden dip (>10% pullback, RSI<35, R²>0.5, volume shrinkage)
  Step 3: Position management (30% → 50% → 100% as price drops further)
  Step 4: Anti-human selling (only sell when trend truly breaks)

This strategy runs PARALLEL to existing strategies — no existing code is modified.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BacktestTrade:
    """Record of a single completed round-trip trade."""
    code: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    holding_days: int
    max_drawdown_during: float  # max drawdown experienced while holding
    exit_reason: str
    position_sizes: list  # history of position size changes


@dataclass
class BacktestResult:
    """Comprehensive backtest result."""
    code: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return_pct: float
    max_single_gain_pct: float
    max_single_loss_pct: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    calmar_ratio: float
    avg_holding_days: float
    pain_index: float  # average max drawdown during each trade
    trades: list  # list of BacktestTrade
    equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    holding_days_distribution: dict = field(default_factory=dict)


class GoldenDipStrategy:
    """Golden Dip Buy Strategy — buy the dip in confirmed bull stocks.

    Parameters:
        r2_bull_threshold:   R² minimum to confirm bull stock (default 0.6)
        r2_dip_threshold:    R² minimum during dip — trend not broken (default 0.5)
        r2_sell_threshold:   R² below which trend is considered broken (default 0.3)
        pullback_pct:        Minimum pullback from recent high to qualify as dip (default 0.10)
        rsi_oversold:        RSI threshold for oversold during dip (default 35)
        rsi_overheat:        RSI threshold for extreme overheat sell (default 90)
        rsi_overheat_days:   Consecutive days RSI > overheat to trigger sell (default 3)
        return_60d_min:      Minimum 60-day return to confirm bull (default 0.20)
        trailing_stop:       Max drawdown from highest price to trigger sell (default 0.25)
        volume_shrink_ratio: Volume shrinkage ratio vs 20d avg to confirm dip (default 0.7)
        position_initial:    Initial position size on first buy (default 0.3)
        position_add1:       Position after first add (5% more drop, default 0.5)
        position_add2:       Position after second add (10% more drop, default 1.0)
        add_drop_pct:        Percentage drop to trigger each add (default 0.05)
    """

    def __init__(
        self,
        r2_bull_threshold: float = 0.6,
        r2_dip_threshold: float = 0.5,
        r2_sell_threshold: float = 0.3,
        pullback_pct: float = 0.10,
        rsi_oversold: float = 35.0,
        rsi_overheat: float = 90.0,
        rsi_overheat_days: int = 3,
        return_60d_min: float = 0.20,
        trailing_stop: float = 0.25,
        volume_shrink_ratio: float = 0.7,
        position_initial: float = 0.3,
        position_add1: float = 0.5,
        position_add2: float = 1.0,
        add_drop_pct: float = 0.05,
    ):
        self.r2_bull_threshold = r2_bull_threshold
        self.r2_dip_threshold = r2_dip_threshold
        self.r2_sell_threshold = r2_sell_threshold
        self.pullback_pct = pullback_pct
        self.rsi_oversold = rsi_oversold
        self.rsi_overheat = rsi_overheat
        self.rsi_overheat_days = rsi_overheat_days
        self.return_60d_min = return_60d_min
        self.trailing_stop = trailing_stop
        self.volume_shrink_ratio = volume_shrink_ratio
        self.position_initial = position_initial
        self.position_add1 = position_add1
        self.position_add2 = position_add2
        self.add_drop_pct = add_drop_pct

    # ─── indicator helpers (pure NumPy) ──────────────────────

    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI series. Returns array of same length (leading NaNs)."""
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
        if y_mean == 0:
            return 0.0
        return slope / y_mean

    @staticmethod
    def calculate_r2_series(prices: np.ndarray, window: int) -> np.ndarray:
        """Rolling R² over the entire price series."""
        prices = np.asarray(prices, dtype=np.float64)
        n = len(prices)
        r2_series = np.full(n, np.nan)
        if n < window:
            return r2_series
        for i in range(window - 1, n):
            segment = prices[i - window + 1: i + 1]
            y = segment
            x = np.arange(window, dtype=np.float64)
            y_mean = np.mean(y)
            ss_tot = np.sum((y - y_mean) ** 2)
            if ss_tot == 0:
                r2_series[i] = 0.0
                continue
            x_mean = np.mean(x)
            slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
            intercept = y_mean - slope * x_mean
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            r2_series[i] = max(1.0 - ss_res / ss_tot, 0.0)
        return r2_series

    # ─── Step 1: Confirm bull stock ──────────────────────────

    def is_bull_stock(self, prices: np.ndarray, volumes: np.ndarray) -> bool:
        """Check if a stock qualifies as a bull stock.

        Criteria:
          - 120-day R² > r2_bull_threshold (clear uptrend)
          - 120-day slope > 0 (direction is up)
          - 60-day return > return_60d_min (actually going up)
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < 120:
            return False

        r2_120 = self.calculate_r2(prices, 120)
        if r2_120 < self.r2_bull_threshold:
            return False

        slope_120 = self.calculate_slope(prices, 120)
        if slope_120 <= 0:
            return False

        ret_60 = (prices[-1] / prices[-61] - 1) if len(prices) >= 61 else 0.0
        if ret_60 < self.return_60d_min:
            return False

        return True

    # ─── Step 2: Detect golden dip ───────────────────────────

    def detect_golden_dip(self, prices: np.ndarray, volumes: np.ndarray) -> dict:
        """Detect if current price is in a golden dip.

        Returns dict with:
          - signal: bool (True if golden dip detected)
          - score: float 0-100 (confidence score)
          - suggested_position: float (recommended position size 0-1)
          - details: dict of individual checks
        """
        prices = np.asarray(prices, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64) if volumes is not None else np.ones(len(prices))

        result = {
            "signal": False,
            "score": 0.0,
            "suggested_position": 0.0,
            "details": {},
        }

        if len(prices) < 120:
            result["details"]["error"] = "insufficient_data"
            return result

        # Check pullback from recent high
        lookback = min(60, len(prices))
        recent_high = np.max(prices[-lookback:])
        current_price = prices[-1]
        pullback = (recent_high - current_price) / recent_high if recent_high > 0 else 0.0

        # RSI check
        rsi = self.calculate_rsi(prices, 14)
        current_rsi = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0

        # R² check (trend still intact during dip)
        r2_120 = self.calculate_r2(prices, 120)

        # Volume shrinkage check
        vol_shrunk = False
        if len(volumes) >= 20:
            vol_recent = np.mean(volumes[-5:]) if np.mean(volumes[-5:]) > 0 else 1.0
            vol_avg_20 = np.mean(volumes[-20:]) if np.mean(volumes[-20:]) > 0 else 1.0
            vol_ratio = vol_recent / vol_avg_20
            vol_shrunk = vol_ratio < self.volume_shrink_ratio
        else:
            vol_ratio = 1.0

        result["details"] = {
            "pullback_pct": pullback,
            "rsi": current_rsi,
            "r2_120": r2_120,
            "volume_ratio": vol_ratio if len(volumes) >= 20 else None,
            "volume_shrunk": vol_shrunk,
        }

        # Score each condition
        score = 0.0

        # Pullback check (30 points)
        if pullback >= self.pullback_pct:
            score += 30.0
            if pullback >= self.pullback_pct * 1.5:
                score += 5.0  # deeper dip = more confidence

        # RSI oversold (30 points)
        if current_rsi < self.rsi_oversold:
            score += 30.0
            if current_rsi < self.rsi_oversold - 10:
                score += 5.0  # deeply oversold

        # R² still decent (20 points)
        if r2_120 >= self.r2_dip_threshold:
            score += 20.0

        # Volume shrinkage (15 points)
        if vol_shrunk:
            score += 15.0

        result["score"] = score

        # Signal = all core conditions met
        core_conditions = (
            pullback >= self.pullback_pct
            and current_rsi < self.rsi_oversold
            and r2_120 >= self.r2_dip_threshold
        )
        result["signal"] = core_conditions

        # Suggested position based on conditions
        if core_conditions:
            result["suggested_position"] = self.position_initial
            if vol_shrunk:
                result["suggested_position"] = self.position_add1  # stronger signal

        return result

    # ─── Step 3: Position management ─────────────────────────

    def position_management(
        self,
        prices: np.ndarray,
        entry_price: float,
        current_position: float,
    ) -> dict:
        """Manage position size based on price action relative to entry.

        Returns dict with:
          - target_position: float (0.0 to 1.0)
          - action: str ("hold", "add", "reduce")
          - reason: str
        """
        prices = np.asarray(prices, dtype=np.float64)
        current_price = prices[-1] if len(prices) > 0 else entry_price

        if entry_price <= 0:
            return {"target_position": current_position, "action": "hold", "reason": "invalid_entry_price"}

        change_from_entry = (current_price - entry_price) / entry_price

        # Price dropped 10% from entry → go full position (check deeper drop first!)
        if change_from_entry <= -self.add_drop_pct * 2 and current_position < self.position_add2:
            return {
                "target_position": self.position_add2,
                "action": "add",
                "reason": f"price_dropped_{abs(change_from_entry)*100:.1f}pct_from_entry",
            }

        # Price dropped 5% from entry → add to position_add1
        if change_from_entry <= -self.add_drop_pct and current_position < self.position_add1:
            return {
                "target_position": self.position_add1,
                "action": "add",
                "reason": f"price_dropped_{abs(change_from_entry)*100:.1f}pct_from_entry",
            }

        # Price recovered above entry → hold
        if change_from_entry > 0:
            return {
                "target_position": current_position,
                "action": "hold",
                "reason": "price_above_entry_hold",
            }

        return {
            "target_position": current_position,
            "action": "hold",
            "reason": "within_normal_range",
        }

    # ─── Step 4: Sell conditions ─────────────────────────────

    def should_sell(
        self,
        prices: np.ndarray,
        entry_price: float,
        highest_price: float,
    ) -> tuple:
        """Check if a held position should be sold (anti-human: don't sell easily).

        Conditions (any one triggers sell):
          1. 120d R² < r2_sell_threshold (trend truly broken)
          2. Drawdown from highest > trailing_stop (stop-loss protection)
          3. RSI > rsi_overheat for rsi_overheat_days consecutive days

        Returns:
            (should_sell: bool, reason: str)
        """
        prices = np.asarray(prices, dtype=np.float64)
        if len(prices) < 15:
            return False, "insufficient_data"

        current_price = prices[-1]

        # 1. Trailing stop: drawdown from highest price
        if highest_price > 0:
            dd = (current_price - highest_price) / highest_price
            if dd < -self.trailing_stop:
                return True, f"trailing_stop_{abs(dd)*100:.1f}pct"

        # 2. Trend breakdown: R² collapsed
        r2_120 = self.calculate_r2(prices, min(120, len(prices)))
        if r2_120 < self.r2_sell_threshold:
            return True, f"r2_breakdown_{r2_120:.3f}"

        # 3. Extreme overheat: RSI > threshold for N consecutive days
        rsi = self.calculate_rsi(prices, 14)
        if len(rsi) >= self.rsi_overheat_days:
            recent_rsi = rsi[-self.rsi_overheat_days:]
            if all(not np.isnan(r) and r > self.rsi_overheat for r in recent_rsi):
                return True, f"rsi_overheat_{self.rsi_overheat_days}d"

        return False, ""

    # ─── Backtest engine ─────────────────────────────────────

    def backtest(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        initial_capital: float = 1_000_000.0,
        dates: Optional[np.ndarray] = None,
        open_prices: Optional[np.ndarray] = None,
        code: str = "",
    ) -> BacktestResult:
        """Run a complete backtest on a single stock's historical data.

        Execution model:
          - Signal generated at T (close)
          - Execution at T+1 open price (or close if open_prices not provided)
          - Position sizing against current capital

        Args:
            prices: Close prices array
            volumes: Volume array
            initial_capital: Starting capital
            dates: Date strings array (optional, for reporting)
            open_prices: Open prices array (for T+1 execution)
            code: Stock code for labeling

        Returns:
            BacktestResult with all statistics
        """
        prices = np.asarray(prices, dtype=np.float64)
        volumes = np.asarray(volumes, dtype=np.float64)
        n = len(prices)

        if open_prices is not None:
            open_prices = np.asarray(open_prices, dtype=np.float64)
        else:
            open_prices = prices.copy()

        if dates is None:
            dates = np.array([str(i) for i in range(n)])

        trades: list[BacktestTrade] = []
        equity = np.full(n, initial_capital)
        cash = initial_capital
        shares = 0.0
        position_ratio = 0.0
        entry_price = 0.0
        entry_idx = -1
        highest_since_entry = 0.0
        max_dd_during_trade = 0.0
        position_history: list = []
        in_position = False

        # Need at least 121 bars to start generating signals
        start_idx = 121

        if n <= start_idx:
            # Not enough data to generate any signals
            return BacktestResult(
                code=code,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_return_pct=0.0,
                max_single_gain_pct=0.0,
                max_single_loss_pct=0.0,
                total_return_pct=0.0,
                annualized_return_pct=0.0,
                max_drawdown_pct=0.0,
                calmar_ratio=0.0,
                avg_holding_days=0.0,
                pain_index=0.0,
                trades=[],
                equity_curve=equity,
                holding_days_distribution={},
            )

        for i in range(start_idx, n):
            # Update equity
            if in_position and shares > 0:
                portfolio_value = cash + shares * prices[i]
            else:
                portfolio_value = cash
            equity[i] = portfolio_value

            if in_position:
                # Track highest price since entry
                if prices[i] > highest_since_entry:
                    highest_since_entry = prices[i]

                # Track max drawdown during trade
                if highest_since_entry > 0:
                    dd_during = (prices[i] - highest_since_entry) / highest_since_entry
                    if dd_during < max_dd_during_trade:
                        max_dd_during_trade = dd_during

                # Check sell conditions (using close prices up to today)
                sell, reason = self.should_sell(
                    prices[:i + 1], entry_price, highest_since_entry
                )

                if sell and i + 1 < n:
                    # Sell at T+1 open
                    sell_price = open_prices[i + 1]
                    cash += shares * sell_price
                    ret_pct = (sell_price - entry_price) / entry_price * 100
                    trades.append(BacktestTrade(
                        code=code,
                        entry_date=str(dates[entry_idx]),
                        exit_date=str(dates[i + 1]),
                        entry_price=entry_price,
                        exit_price=sell_price,
                        return_pct=ret_pct,
                        holding_days=i + 1 - entry_idx,
                        max_drawdown_during=abs(max_dd_during_trade) * 100,
                        exit_reason=reason,
                        position_sizes=position_history.copy(),
                    ))
                    shares = 0.0
                    position_ratio = 0.0
                    in_position = False
                    position_history = []
                    continue

                # Position management: check if we should add
                if position_ratio < 1.0:
                    pm = self.position_management(
                        prices[:i + 1], entry_price, position_ratio
                    )
                    if pm["action"] == "add" and i + 1 < n:
                        new_ratio = pm["target_position"]
                        add_amount = (new_ratio - position_ratio) * initial_capital
                        if add_amount > 0 and cash >= add_amount:
                            add_price = open_prices[i + 1]
                            add_shares = add_amount / add_price
                            shares += add_shares
                            cash -= add_shares * add_price
                            # Update average entry price
                            total_cost = entry_price * (shares - add_shares) + add_price * add_shares
                            entry_price = total_cost / shares
                            position_ratio = new_ratio
                            position_history.append((str(dates[i + 1]), new_ratio))

            else:
                # Not in position — check for entry signal
                # Step 1: Is it a bull stock?
                if not self.is_bull_stock(prices[:i + 1], volumes[:i + 1]):
                    continue

                # Step 2: Is this a golden dip?
                dip = self.detect_golden_dip(prices[:i + 1], volumes[:i + 1])
                if not dip["signal"]:
                    continue

                # Execute buy at T+1 open
                if i + 1 < n:
                    buy_price = open_prices[i + 1]
                    position_ratio = dip["suggested_position"]
                    invest_amount = position_ratio * initial_capital
                    if cash >= invest_amount:
                        shares = invest_amount / buy_price
                        cash -= shares * buy_price
                        entry_price = buy_price
                        entry_idx = i + 1
                        highest_since_entry = buy_price
                        max_dd_during_trade = 0.0
                        in_position = True
                        position_history = [(str(dates[i + 1]), position_ratio)]

        # Close any remaining position at last price
        if in_position and shares > 0:
            sell_price = prices[-1]
            ret_pct = (sell_price - entry_price) / entry_price * 100
            trades.append(BacktestTrade(
                code=code,
                entry_date=str(dates[entry_idx]),
                exit_date=str(dates[-1]),
                entry_price=entry_price,
                exit_price=sell_price,
                return_pct=ret_pct,
                holding_days=n - 1 - entry_idx,
                max_drawdown_during=abs(max_dd_during_trade) * 100,
                exit_reason="end_of_data",
                position_sizes=position_history.copy(),
            ))
            cash += shares * sell_price
            shares = 0.0

        # Fill equity for early period
        for i in range(start_idx):
            equity[i] = initial_capital

        # ── Compute statistics ──
        total_trades = len(trades)
        if total_trades == 0:
            return BacktestResult(
                code=code,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_return_pct=0.0,
                max_single_gain_pct=0.0,
                max_single_loss_pct=0.0,
                total_return_pct=0.0,
                annualized_return_pct=0.0,
                max_drawdown_pct=0.0,
                calmar_ratio=0.0,
                avg_holding_days=0.0,
                pain_index=0.0,
                trades=[],
                equity_curve=equity,
                holding_days_distribution={},
            )

        returns = [t.return_pct for t in trades]
        winning = [r for r in returns if r > 0]
        losing = [r for r in returns if r <= 0]

        win_rate = len(winning) / total_trades * 100

        avg_return = np.mean(returns)
        max_gain = max(returns) if returns else 0.0
        max_loss = min(returns) if returns else 0.0

        # Total return from equity curve
        final_equity = cash
        total_return_pct = (final_equity / initial_capital - 1) * 100

        # Annualized return
        trading_days = n
        years = trading_days / 252.0
        if years > 0 and final_equity > 0:
            annualized = (final_equity / initial_capital) ** (1.0 / years) - 1
            annualized_return_pct = annualized * 100
        else:
            annualized_return_pct = 0.0

        # Max drawdown from equity curve
        peak = np.maximum.accumulate(equity)
        dd = np.where(peak > 0, (equity - peak) / peak, 0.0)
        max_drawdown_pct = abs(float(np.min(dd))) * 100

        # Calmar ratio
        calmar = annualized_return_pct / max_drawdown_pct if max_drawdown_pct > 0 else 0.0

        # Holding days
        holding_days_list = [t.holding_days for t in trades]
        avg_holding = np.mean(holding_days_list)

        # Holding days distribution
        buckets = {"<7d": 0, "7-30d": 0, "30-90d": 0, "90-180d": 0, ">180d": 0}
        for d in holding_days_list:
            if d < 7:
                buckets["<7d"] += 1
            elif d < 30:
                buckets["7-30d"] += 1
            elif d < 90:
                buckets["30-90d"] += 1
            elif d < 180:
                buckets["90-180d"] += 1
            else:
                buckets[">180d"] += 1

        # Pain index: average of max drawdown during each trade
        pain = np.mean([t.max_drawdown_during for t in trades])

        return BacktestResult(
            code=code,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            avg_return_pct=avg_return,
            max_single_gain_pct=max_gain,
            max_single_loss_pct=max_loss,
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            calmar_ratio=calmar,
            avg_holding_days=avg_holding,
            pain_index=pain,
            trades=trades,
            equity_curve=equity,
            holding_days_distribution=buckets,
        )
