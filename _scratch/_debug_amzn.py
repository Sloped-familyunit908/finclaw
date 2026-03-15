import asyncio
from agents.backtester_v5 import BacktesterV5
from benchmark_v6 import sim

# AMZN (Bull 2): drift=0.30, vol=0.35
h = sim(180, 252, 0.30, 0.35, 1628)

async def main():
    bt = BacktesterV5(initial_capital=10000)
    r = await bt.run('AMZN', 'test', h)
    bh = h[-1]['price'] / h[0]['price'] - 1
    bh20 = h[-1]['price'] / h[20]['price'] - 1
    print(f"total={r.total_return*100:.1f}% bh_0={bh*100:.1f}% bh_20={bh20*100:.1f}%")
    print(f"alpha_0={(r.total_return-bh)*100:.1f}% alpha_20={(r.total_return-bh20)*100:.1f}%")
    print(f"trades={r.total_trades}")
    for t in r.trades:
        d1 = t.entry_time.strftime('%m/%d')
        d2 = t.exit_time.strftime('%m/%d')
        print(f"  {d1}->{d2} entry={t.entry_price:.0f} exit={t.exit_price:.0f} pnl={t.pnl_pct*100:+.1f}% {t.signal_source}")

asyncio.run(main())
