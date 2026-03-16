"""
FinClaw: Full Backtest Analysis Workflow
=========================================
Complete workflow: data → strategy → backtest → analysis → visualization.

Designed to run as a script or in Jupyter notebooks.

Usage:
    python backtest_analysis.py
    # or: jupyter notebook backtest_analysis.ipynb

Prerequisites:
    pip install finclaw-ai[ml] matplotlib
"""

from finclaw_ai import FinClaw
from finclaw_ai.strategies import BaseStrategy
from finclaw_ai.analytics import BacktestAnalyzer

fc = FinClaw()


# --- Step 1: Define Strategy ---
class RSIMeanReversion(BaseStrategy):
    """Buy when RSI is oversold, sell when overbought."""

    name = "rsi_mean_reversion"

    def __init__(self, rsi_period=14, oversold=30, overbought=70):
        super().__init__()
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, bar, history):
        rsi = bar.get("rsi_14")
        if rsi is None:
            return
        if not self.in_position and rsi < self.oversold:
            self.buy(reason=f"RSI oversold ({rsi:.1f})")
        elif self.in_position and rsi > self.overbought:
            self.sell(reason=f"RSI overbought ({rsi:.1f})")


# --- Step 2: Run Backtest ---
strategy = RSIMeanReversion(oversold=30, overbought=70)

result = fc.backtest(
    symbol="AAPL",
    strategy=strategy,
    start="2022-01-01",
    end="2024-12-31",
    initial_capital=100_000,
    commission=0.001,  # 0.1% per trade
)

# --- Step 3: Analyze ---
analyzer = BacktestAnalyzer(result)

print("=" * 50)
print("  RSI Mean Reversion — AAPL (2022-2024)")
print("=" * 50)

# Performance metrics
metrics = analyzer.get_metrics()
print(f"\n📊 Performance")
print(f"  Total Return:      {metrics['total_return']:+.2f}%")
print(f"  Annual Return:     {metrics['annual_return']:+.2f}%")
print(f"  Benchmark (B&H):   {metrics['benchmark_return']:+.2f}%")
print(f"  Alpha:             {metrics['alpha']:+.2f}%")

print(f"\n📈 Risk")
print(f"  Volatility:        {metrics['volatility']:.2f}%")
print(f"  Sharpe Ratio:      {metrics['sharpe_ratio']:.2f}")
print(f"  Sortino Ratio:     {metrics['sortino_ratio']:.2f}")
print(f"  Max Drawdown:      {metrics['max_drawdown']:.2f}%")
print(f"  Calmar Ratio:      {metrics['calmar_ratio']:.2f}")

print(f"\n🔄 Trading")
print(f"  Total Trades:      {metrics['total_trades']}")
print(f"  Win Rate:          {metrics['win_rate']:.1f}%")
print(f"  Profit Factor:     {metrics['profit_factor']:.2f}")
print(f"  Avg Win:           {metrics['avg_win']:+.2f}%")
print(f"  Avg Loss:          {metrics['avg_loss']:+.2f}%")
print(f"  Expectancy:        ${metrics['expectancy']:,.2f}")

# Monthly returns
print(f"\n📅 Monthly Returns")
monthly = analyzer.get_monthly_returns()
for year in sorted(monthly.keys()):
    returns = monthly[year]
    yr_total = sum(returns.values())
    months_str = " ".join(f"{returns.get(m, 0):+5.1f}" for m in range(1, 13))
    print(f"  {year}: {months_str}  | {yr_total:+.1f}%")

# --- Step 4: Export ---
# Save results to file
analyzer.export_html("backtest_report.html")
print(f"\n✅ Report saved to backtest_report.html")
