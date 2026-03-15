"""Diagnose trade-by-trade on key scenarios."""
import asyncio
from agents.backtester_v5 import BacktesterV5
from benchmark_v6 import sim, benchmark_avg

scenarios = [
    ("NVDA",  sim(500, 252, 0.80, 0.50, 1395)),
    ("AMZN",  sim(180, 252, 0.30, 0.35, 1628)),
    ("AAPL",  sim(180, 252, 0.15, 0.25, 1002)),
    ("TSLA",  sim(250, 252, 0.40, 0.65, 1525)),
    ("Moutai",sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)),
]

async def main():
    for name, h in scenarios:
        bt  = BacktesterV5(initial_capital=10000)
        r   = await bt.run(name, "test", h)
        bh0 = h[-1]["price"] / h[0]["price"] - 1
        ahf = benchmark_avg(h, "selective", 7)
        print(f"\n{'='*60}")
        print(f"{name}: WT={r.total_return*100:+.1f}% BH0={bh0*100:+.1f}% alpha={( r.total_return-bh0)*100:+.1f}%  AHF_alpha={ahf['alpha']*100:+.1f}%  trades={r.total_trades}")
        for t in r.trades:
            d1 = t.entry_time.strftime('%m/%d')
            d2 = t.exit_time.strftime('%m/%d')
            print(f"  {d1}->{d2}  e={t.entry_price:.0f} x={t.exit_price:.0f}  pnl={t.pnl_pct*100:+.1f}%  {t.signal_source}")

asyncio.run(main())
