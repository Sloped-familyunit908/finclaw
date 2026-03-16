"""
FinClaw: Write Your Own Strategy
=================================
Template for creating custom trading strategies.

Usage:
    python custom_strategy.py
"""

from finclaw_ai import FinClaw
from finclaw_ai.strategies import BaseStrategy


class MomentumBreakout(BaseStrategy):
    """
    Custom strategy: Buy when price breaks above 20-day high
    with above-average volume. Sell on trailing stop.
    """

    name = "momentum_breakout"

    def __init__(self, lookback=20, volume_factor=1.5, trailing_stop_pct=5.0):
        super().__init__()
        self.lookback = lookback
        self.volume_factor = volume_factor
        self.trailing_stop_pct = trailing_stop_pct

    def on_bar(self, bar, history):
        """Called on each new price bar."""
        if len(history) < self.lookback:
            return  # Not enough data yet

        recent = history[-self.lookback:]
        high_20d = max(b["high"] for b in recent)
        avg_volume = sum(b["volume"] for b in recent) / self.lookback

        # Entry: price breaks above 20-day high with strong volume
        if not self.in_position:
            if bar["close"] > high_20d and bar["volume"] > avg_volume * self.volume_factor:
                self.buy(reason=f"Breakout above ${high_20d:.2f}, volume {bar['volume']/avg_volume:.1f}x avg")

        # Exit: trailing stop
        else:
            drop_from_peak = (self.peak_price - bar["close"]) / self.peak_price * 100
            if drop_from_peak > self.trailing_stop_pct:
                self.sell(reason=f"Trailing stop hit ({drop_from_peak:.1f}% from peak)")


# --- Run it ---
fc = FinClaw()

strategy = MomentumBreakout(
    lookback=20,
    volume_factor=1.5,
    trailing_stop_pct=5.0,
)

result = fc.backtest(
    symbol="NVDA",
    strategy=strategy,
    start="2024-01-01",
    end="2024-12-31",
    initial_capital=25_000,
)

print("=== Custom Strategy: Momentum Breakout on NVDA ===")
print(f"Total Return:    {result['total_return']:+.2f}%")
print(f"Sharpe Ratio:    {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown:    {result['max_drawdown']:.2f}%")
print(f"Total Trades:    {result['total_trades']}")

# Show trade log
print(f"\n=== Trade Log (last 5) ===")
for trade in result["trades"][-5:]:
    print(f"  {trade['date']}  {trade['side']:<5}  ${trade['price']:.2f}  {trade['reason']}")
