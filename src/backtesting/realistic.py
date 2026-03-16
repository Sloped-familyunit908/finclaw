"""
Realistic Backtesting Engine
Production-grade backtester with slippage, commissions, market impact,
partial fills, limit/market/stop orders, and day-by-day simulation.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any, Callable


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class FillStatus(Enum):
    UNFILLED = "unfilled"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class BacktestConfig:
    """Configuration for realistic backtesting."""
    initial_capital: float = 100_000.0
    slippage_bps: float = 5.0          # basis points per trade
    commission_rate: float = 0.001      # 0.1% per trade
    impact_coeff: float = 0.1           # market impact coefficient
    risk_free_rate: float = 0.05        # annual risk-free rate
    margin_requirement: float = 1.0     # 1.0 = no margin, 0.5 = 2x leverage
    max_position_pct: float = 0.95      # max % of capital in single position
    allow_short: bool = False
    partial_fill_prob: float = 0.0      # probability of partial fill (0-1)
    partial_fill_min_pct: float = 0.5   # minimum fill percentage when partial
    order_ttl_bars: int = 1             # bars before unfilled limit orders expire


@dataclass
class Order:
    """A pending or executed order."""
    id: int
    side: OrderSide
    order_type: OrderType
    quantity: float
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    status: FillStatus = FillStatus.UNFILLED
    created_bar: int = 0
    filled_bar: Optional[int] = None
    commission: float = 0.0
    slippage_cost: float = 0.0
    impact_cost: float = 0.0


@dataclass
class TradeRecord:
    """A completed round-trip trade."""
    entry_bar: int
    exit_bar: int
    entry_price: float
    exit_price: float
    quantity: float
    side: str
    pnl: float
    pnl_pct: float
    commission: float
    slippage_cost: float
    impact_cost: float
    holding_bars: int
    entry_date: Optional[str] = None
    exit_date: Optional[str] = None


@dataclass
class BacktestResult:
    """Complete realistic backtest results."""
    # Identity
    strategy_name: str = ""
    config: Optional[BacktestConfig] = None

    # Returns
    total_return: float = 0.0
    annualized_return: float = 0.0
    cagr: float = 0.0

    # Risk
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    volatility: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_return: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    expectancy: float = 0.0

    # Costs
    total_commission: float = 0.0
    total_slippage: float = 0.0
    total_market_impact: float = 0.0
    total_costs: float = 0.0
    cost_drag_pct: float = 0.0  # total costs / initial capital

    # Series
    equity_curve: list[float] = field(default_factory=list)
    drawdown_curve: list[float] = field(default_factory=list)
    daily_returns: list[float] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    positions_over_time: list[float] = field(default_factory=list)

    # Benchmark
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None

    def summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            f"║  REALISTIC BACKTEST: {self.strategy_name:<39}║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Total Return:     {self.total_return:>+10.2%}   CAGR: {self.cagr:>+8.2%}          ║",
            f"║  Sharpe:           {self.sharpe_ratio:>10.2f}   Sortino: {self.sortino_ratio:>8.2f}        ║",
            f"║  Max Drawdown:     {self.max_drawdown:>10.2%}   Calmar: {self.calmar_ratio:>9.2f}       ║",
            f"║  Volatility:       {self.volatility:>10.2%}   VaR95: {self.var_95:>10.2%}       ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Trades: {self.total_trades:<6} Win Rate: {self.win_rate:>6.1%}  PF: {self.profit_factor:>6.2f}        ║",
            f"║  Avg Win: {self.avg_win:>+7.2%}  Avg Loss: {self.avg_loss:>+7.2%}                   ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Costs: Commission=${self.total_commission:>8.2f}  "
            f"Slip=${self.total_slippage:>8.2f}             ║",
            f"║         Impact=${self.total_market_impact:>8.2f}  "
            f"Total=${self.total_costs:>8.2f}  ({self.cost_drag_pct:>+.2%})    ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)


class SlippageModel:
    """Model price slippage based on basis points."""

    def __init__(self, bps: float = 5.0):
        self.bps = bps

    def apply(self, price: float, side: OrderSide, volume: float = 0) -> float:
        """Return the slipped price (worse for the trader)."""
        slip_pct = self.bps / 10_000
        if side == OrderSide.BUY:
            return price * (1 + slip_pct)
        return price * (1 - slip_pct)

    def cost(self, price: float, quantity: float) -> float:
        return abs(quantity) * price * (self.bps / 10_000)


class CommissionModel:
    """Model trading commissions."""

    def __init__(self, rate: float = 0.001, minimum: float = 0.0):
        self.rate = rate
        self.minimum = minimum

    def calculate(self, price: float, quantity: float) -> float:
        return max(abs(quantity) * price * self.rate, self.minimum)


class MarketImpactModel:
    """
    Simple market impact model.
    Impact proportional to sqrt(quantity / avg_volume) * coefficient.
    """

    def __init__(self, coeff: float = 0.1):
        self.coeff = coeff

    def impact_bps(self, quantity: float, avg_volume: float) -> float:
        if avg_volume <= 0:
            return 0.0
        participation = abs(quantity) / avg_volume
        return self.coeff * math.sqrt(participation) * 10_000

    def apply(self, price: float, side: OrderSide, quantity: float,
              avg_volume: float) -> float:
        impact = self.impact_bps(quantity, avg_volume) / 10_000
        if side == OrderSide.BUY:
            return price * (1 + impact)
        return price * (1 - impact)

    def cost(self, price: float, quantity: float, avg_volume: float) -> float:
        impact = self.impact_bps(quantity, avg_volume) / 10_000
        return abs(quantity) * price * impact


class SimpleOrderBook:
    """Manages pending orders and simulates fills."""

    def __init__(self):
        self._orders: list[Order] = []
        self._next_id = 1

    def submit(self, side: OrderSide, order_type: OrderType, quantity: float,
               limit_price: Optional[float] = None, stop_price: Optional[float] = None,
               bar: int = 0) -> Order:
        order = Order(
            id=self._next_id, side=side, order_type=order_type,
            quantity=quantity, limit_price=limit_price, stop_price=stop_price,
            created_bar=bar,
        )
        self._next_id += 1
        self._orders.append(order)
        return order

    def cancel_all(self):
        for o in self._orders:
            if o.status in (FillStatus.UNFILLED, FillStatus.PARTIAL):
                o.status = FillStatus.CANCELLED
        self._orders = []

    def process_bar(self, bar: int, open_price: float, high: float, low: float,
                    close: float, volume: float, config: BacktestConfig,
                    slippage: SlippageModel, commission: CommissionModel,
                    impact: MarketImpactModel) -> list[Order]:
        """Process all pending orders against this bar's OHLCV. Returns filled orders."""
        filled = []
        remaining = []

        for order in self._orders:
            if order.status in (FillStatus.FILLED, FillStatus.CANCELLED, FillStatus.EXPIRED):
                continue

            # Check expiry
            if bar - order.created_bar >= config.order_ttl_bars and \
               order.order_type != OrderType.MARKET:
                order.status = FillStatus.EXPIRED
                continue

            can_fill, fill_price = self._check_fill(order, open_price, high, low, close)
            if can_fill:
                # Apply slippage
                slipped = slippage.apply(fill_price, order.side, volume)
                # Apply market impact
                impacted = impact.apply(slipped, order.side, order.quantity, volume)

                # Determine fill quantity (partial fills)
                import random
                if config.partial_fill_prob > 0 and random.random() < config.partial_fill_prob:
                    fill_qty = order.quantity * (
                        config.partial_fill_min_pct +
                        random.random() * (1 - config.partial_fill_min_pct)
                    )
                    order.filled_quantity = fill_qty
                    order.status = FillStatus.PARTIAL
                else:
                    fill_qty = order.quantity
                    order.filled_quantity = fill_qty
                    order.status = FillStatus.FILLED

                order.filled_price = impacted
                order.filled_bar = bar
                order.commission = commission.calculate(impacted, fill_qty)
                order.slippage_cost = slippage.cost(fill_price, fill_qty)
                order.impact_cost = impact.cost(slipped, fill_qty, volume)

                filled.append(order)

                # Keep partial orders alive
                if order.status == FillStatus.PARTIAL:
                    order.quantity -= fill_qty
                    order.status = FillStatus.UNFILLED
                    remaining.append(order)
            else:
                remaining.append(order)

        self._orders = remaining
        return filled

    @staticmethod
    def _check_fill(order: Order, open_p: float, high: float, low: float,
                    close: float) -> tuple[bool, float]:
        if order.order_type == OrderType.MARKET:
            return True, open_p

        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY and low <= (order.limit_price or 0):
                return True, min(open_p, order.limit_price or open_p)
            if order.side == OrderSide.SELL and high >= (order.limit_price or 0):
                return True, max(open_p, order.limit_price or open_p)

        if order.order_type == OrderType.STOP:
            if order.side == OrderSide.SELL and low <= (order.stop_price or 0):
                return True, order.stop_price or close
            if order.side == OrderSide.BUY and high >= (order.stop_price or 0):
                return True, order.stop_price or close

        if order.order_type == OrderType.STOP_LIMIT:
            if order.stop_price and order.limit_price:
                triggered = False
                if order.side == OrderSide.SELL and low <= order.stop_price:
                    triggered = True
                elif order.side == OrderSide.BUY and high >= order.stop_price:
                    triggered = True
                if triggered:
                    if order.side == OrderSide.BUY and low <= order.limit_price:
                        return True, order.limit_price
                    if order.side == OrderSide.SELL and high >= order.limit_price:
                        return True, order.limit_price

        return False, 0.0

    @property
    def pending_count(self) -> int:
        return len(self._orders)


class RealisticBacktester:
    """
    Production-grade backtester with realistic fills, costs, and risk tracking.

    Usage:
        config = BacktestConfig(slippage_bps=5, commission_rate=0.001)
        bt = RealisticBacktester(config)
        result = await bt.run(strategy, data, benchmark=spy_prices)
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.slippage_model = SlippageModel(self.config.slippage_bps)
        self.commission_model = CommissionModel(self.config.commission_rate)
        self.market_impact = MarketImpactModel(self.config.impact_coeff)
        self.order_book = SimpleOrderBook()

    async def run(
        self,
        strategy: Any,
        data: list[dict],
        benchmark: Optional[list[float]] = None,
    ) -> BacktestResult:
        """
        Run day-by-day simulation.

        Args:
            strategy: object with generate_signal(prices) -> signal str
                      or a callable(prices) -> "buy"/"sell"/"hold"
            data: list of dicts with keys: price, (high, low, open, volume, date)
            benchmark: optional benchmark price series for comparison
        """
        if not data or len(data) < 30:
            raise ValueError("Need at least 30 bars for realistic backtest")

        capital = self.config.initial_capital
        position = 0.0
        entry_price = 0.0
        entry_bar = 0
        trades: list[TradeRecord] = []
        equity_curve = []
        positions_ts = []

        total_commission = 0.0
        total_slippage = 0.0
        total_impact = 0.0

        prices = [self._get_price(d) for d in data]

        for i in range(len(data)):
            bar = data[i]
            price = prices[i]
            high = bar.get("high", price * 1.005)
            low = bar.get("low", price * 0.995)
            open_p = bar.get("open", price)
            volume = bar.get("volume", 1_000_000)

            # Process pending orders
            filled = self.order_book.process_bar(
                i, open_p, high, low, price, volume,
                self.config, self.slippage_model, self.commission_model,
                self.market_impact,
            )

            for order in filled:
                total_commission += order.commission
                total_slippage += order.slippage_cost
                total_impact += order.impact_cost
                capital -= order.commission

                if order.side == OrderSide.BUY and position == 0:
                    qty = order.filled_quantity
                    cost = qty * order.filled_price
                    capital -= cost
                    position = qty
                    entry_price = order.filled_price
                    entry_bar = i
                elif order.side == OrderSide.SELL and position > 0:
                    qty = min(order.filled_quantity, position)
                    proceeds = qty * order.filled_price
                    capital += proceeds
                    pnl = (order.filled_price - entry_price) * qty
                    pnl_pct = (order.filled_price / entry_price - 1) if entry_price > 0 else 0
                    trades.append(TradeRecord(
                        entry_bar=entry_bar, exit_bar=i,
                        entry_price=entry_price, exit_price=order.filled_price,
                        quantity=qty, side="long",
                        pnl=pnl, pnl_pct=pnl_pct,
                        commission=order.commission,
                        slippage_cost=order.slippage_cost,
                        impact_cost=order.impact_cost,
                        holding_bars=i - entry_bar,
                        entry_date=str(data[entry_bar].get("date", "")),
                        exit_date=str(bar.get("date", "")),
                    ))
                    position -= qty
                    if position <= 0:
                        position = 0
                        entry_price = 0

            # Portfolio value
            port_value = capital + position * price
            equity_curve.append(port_value)
            positions_ts.append(position * price / max(port_value, 1))

            # Generate signal (skip first 20 bars for warmup)
            if i >= 20:
                signal = self._get_signal(strategy, prices[:i + 1])
                if signal == "buy" and position == 0:
                    max_spend = port_value * self.config.max_position_pct
                    qty = max_spend / price if price > 0 else 0
                    if qty > 0:
                        self.order_book.submit(
                            OrderSide.BUY, OrderType.MARKET, qty, bar=i,
                        )
                elif signal == "sell" and position > 0:
                    self.order_book.submit(
                        OrderSide.SELL, OrderType.MARKET, position, bar=i,
                    )

        # Compute metrics
        result = self._compute_metrics(
            equity_curve, trades, positions_ts,
            total_commission, total_slippage, total_impact,
            benchmark, prices,
        )
        result.config = self.config
        return result

    def _get_price(self, bar: dict) -> float:
        if isinstance(bar, (int, float)):
            return float(bar)
        return float(bar.get("price", bar.get("close", 0)))

    def _get_signal(self, strategy: Any, prices: list[float]) -> str:
        if callable(strategy) and not hasattr(strategy, "generate_signal"):
            return strategy(prices)
        if hasattr(strategy, "generate_signal"):
            sig = strategy.generate_signal(prices)
            return getattr(sig, "signal", str(sig)) if sig else "hold"
        if hasattr(strategy, "score_single"):
            return getattr(strategy.score_single(prices), "signal", "hold")
        return "hold"

    def _compute_metrics(
        self, equity: list[float], trades: list[TradeRecord],
        positions_ts: list[float],
        total_comm: float, total_slip: float, total_impact: float,
        benchmark: Optional[list[float]], prices: list[float],
    ) -> BacktestResult:
        if not equity or equity[0] <= 0:
            return BacktestResult()

        initial = equity[0]
        final = equity[-1]
        total_ret = final / initial - 1
        n_bars = len(equity)
        years = max(n_bars / 252, 0.01)
        cagr = (final / initial) ** (1 / years) - 1 if final > 0 else -1

        # Daily returns
        daily_rets = [(equity[i] / equity[i - 1] - 1) for i in range(1, len(equity))]

        # Volatility
        vol = _std(daily_rets) * math.sqrt(252) if len(daily_rets) > 1 else 0

        # Sharpe
        avg_ret = sum(daily_rets) / len(daily_rets) * 252 if daily_rets else 0
        rf = self.config.risk_free_rate
        sharpe = (avg_ret - rf) / max(vol, 0.001)

        # Sortino
        down = [r for r in daily_rets if r < 0]
        down_dev = math.sqrt(sum(r ** 2 for r in down) / max(len(down), 1)) * math.sqrt(252) if down else 0.001
        sortino = (avg_ret - rf) / max(down_dev, 0.001)

        # Drawdown
        peak = equity[0]
        max_dd = 0.0
        dd_curve = []
        dd_start = 0
        max_dd_dur = 0
        in_dd = False
        for i, eq in enumerate(equity):
            if eq >= peak:
                peak = eq
                if in_dd:
                    max_dd_dur = max(max_dd_dur, i - dd_start)
                    in_dd = False
            elif not in_dd:
                dd_start = i
                in_dd = True
            dd = (eq - peak) / peak if peak > 0 else 0
            dd_curve.append(dd)
            max_dd = min(max_dd, dd)

        calmar = cagr / max(abs(max_dd), 0.001) if max_dd != 0 else 0

        # VaR / CVaR
        sorted_rets = sorted(daily_rets)
        idx_5 = max(int(len(sorted_rets) * 0.05), 1)
        var_95 = sorted_rets[idx_5 - 1] if sorted_rets else 0
        cvar_95 = sum(sorted_rets[:idx_5]) / max(idx_5, 1) if sorted_rets else 0

        # Trade stats
        n_trades = len(trades)
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = len(wins) / max(n_trades, 1)
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        pf = gross_profit / max(gross_loss, 0.01)
        avg_win = sum(t.pnl_pct for t in wins) / max(len(wins), 1)
        avg_loss = sum(t.pnl_pct for t in losses) / max(len(losses), 1)
        avg_trade = sum(t.pnl_pct for t in trades) / max(n_trades, 1)
        expectancy = sum(t.pnl for t in trades) / max(n_trades, 1)

        # Consecutive wins/losses
        max_cw = max_cl = cw = cl = 0
        for t in trades:
            if t.pnl > 0:
                cw += 1; cl = 0
            else:
                cl += 1; cw = 0
            max_cw = max(max_cw, cw)
            max_cl = max(max_cl, cl)

        total_costs = total_comm + total_slip + total_impact

        # Benchmark
        bench_ret = alpha_val = beta_val = ir = None
        if benchmark and len(benchmark) >= len(prices):
            n = min(len(prices), len(benchmark))
            bench_ret = (benchmark[n - 1] / benchmark[0] - 1) if benchmark[0] > 0 else 0
            s_rets = daily_rets[:n - 1]
            b_rets = [(benchmark[i] / benchmark[i - 1] - 1) for i in range(1, n)]
            min_len = min(len(s_rets), len(b_rets))
            if min_len > 2:
                s_rets = s_rets[:min_len]
                b_rets = b_rets[:min_len]
                cov = _cov(s_rets, b_rets)
                var_b = _var(b_rets)
                beta_val = cov / max(var_b, 1e-10)
                mean_s = sum(s_rets) / len(s_rets) * 252
                mean_b = sum(b_rets) / len(b_rets) * 252
                alpha_val = mean_s - beta_val * mean_b
                excess = [s - b for s, b in zip(s_rets, b_rets)]
                te = _std(excess) * math.sqrt(252)
                ir = (sum(excess) / len(excess) * 252) / max(te, 0.001)

        return BacktestResult(
            total_return=total_ret, annualized_return=cagr, cagr=cagr,
            sharpe_ratio=sharpe, sortino_ratio=sortino, calmar_ratio=calmar,
            max_drawdown=max_dd, max_drawdown_duration=max_dd_dur,
            volatility=vol, downside_deviation=down_dev,
            var_95=var_95, cvar_95=cvar_95,
            total_trades=n_trades, winning_trades=len(wins), losing_trades=len(losses),
            win_rate=win_rate, profit_factor=pf,
            avg_win=avg_win, avg_loss=avg_loss, avg_trade_return=avg_trade,
            max_consecutive_wins=max_cw, max_consecutive_losses=max_cl,
            expectancy=expectancy,
            total_commission=total_comm, total_slippage=total_slip,
            total_market_impact=total_impact, total_costs=total_costs,
            cost_drag_pct=total_costs / max(initial, 1),
            equity_curve=equity, drawdown_curve=dd_curve,
            daily_returns=daily_rets, trades=trades,
            positions_over_time=positions_ts,
            benchmark_return=bench_ret, alpha=alpha_val,
            beta=beta_val, information_ratio=ir,
        )


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _var(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def _cov(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    return sum((x[i] - mx) * (y[i] - my) for i in range(n)) / (n - 1)
