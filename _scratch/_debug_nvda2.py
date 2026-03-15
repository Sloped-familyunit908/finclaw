import asyncio
from agents.backtester_v5 import BacktesterV5
from benchmark_v6 import sim

h = sim(500, 252, 0.80, 0.50, 1395)
bh = h[-1]['price']/h[0]['price'] - 1

async def main():
    bt = BacktesterV5(initial_capital=10000)
    r = await bt.run('NVDA', 'test', h)
    print(f"NVDA: total={r.total_return*100:.1f}% bh={bh*100:.1f}% alpha={(r.total_return-bh)*100:.1f}% trades={r.total_trades}")
    for t in r.trades:
        d1 = t.entry_time.strftime('%m/%d')
        d2 = t.exit_time.strftime('%m/%d')
        print(f"  {d1}->{d2} entry={t.entry_price:.0f} exit={t.exit_price:.0f} pnl={t.pnl_pct*100:+.1f}% {t.signal_source}")

asyncio.run(main())
