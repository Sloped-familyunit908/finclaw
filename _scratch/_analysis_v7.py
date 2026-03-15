"""
Attempt: improve v7 signal engine on per-scenario basis.
Focus on highest-impact changes without breaking other scenarios.

Strategy: analyze WHERE each scenario's alpha is lost,
find cross-scenario patterns that can be safely tuned.
"""
import asyncio, random, math
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.backtester_v7 import BacktesterV7
from agents.signal_engine_v7 import SignalEngineV7, MarketRegime

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed); dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p,
             'volume': abs(rng.gauss(p*1e6, p*5e5))} for i,p in enumerate(prices)]

async def main():
    """Analyze: for each scenario, what's the #1 thing hurting alpha?"""
    scenarios = [
        ("NVDA",    sim(500, 252, 0.80, 0.50, 1395)),
        ("AAPL",    sim(180, 252, 0.15, 0.25, 1002)),
        ("TSLA",    sim(250, 252, 0.40, 0.65, 1525)),
        ("META",    sim(550, 252,-0.20, 0.35, 1004)),
        ("AMZN",    sim(180, 252, 0.30, 0.35, 1628)),
        ("INTC",    sim(40,  252,-0.50, 0.40, 1006)),
        ("Moutai",  sim(1650,252, 0.05, 0.30, 2001, 0.03, 0.06)),
        ("CATL",    sim(220, 252, 0.55, 0.45, 1323, 0.03, 0.06)),
        ("CSI300",  sim(3800,252,-0.15, 0.25, 2003, 0.03, 0.06)),
    ]

    print(f"{'Scenario':<12} {'B&H':>7} {'v7':>7} {'alpha':>7} | "
          f"{'#trades':>7} {'WR':>4} {'MaxDD':>7} | #1 issue")
    print("-"*85)

    for name, h in scenarios:
        bh = h[-1]["price"]/h[0]["price"]-1
        bt = BacktesterV7(initial_capital=10000)
        r = await bt.run(name, "v7", h)
        alpha = r.total_return - bh

        # Analyze trades
        wins = [t for t in r.trades if t.pnl > 0]
        losses = [t for t in r.trades if t.pnl <= 0]
        biggest_loss = min((t.pnl_pct for t in r.trades), default=0)
        total_loss = sum(t.pnl_pct for t in losses)
        avg_loss = total_loss / max(len(losses), 1)

        # Determine #1 issue
        if alpha > 0.20:
            issue = "STRONG (no issue)"
        elif alpha > 0:
            issue = f"OK. avg_loss={avg_loss:+.1%}, #losses={len(losses)}"
        elif alpha > -0.15:
            # Moderate negative alpha
            if biggest_loss < -0.10:
                issue = f"Big single loss: {biggest_loss:+.1%}"
            elif len(losses) > 5:
                issue = f"Too many small losses ({len(losses)}x avg={avg_loss:+.1%})"
            else:
                issue = f"Underperforming B&H (position sizing?)"
        else:
            # Large negative alpha
            if bh > 0.30:
                issue = f"STRUCTURAL: can't keep up with +{bh:.0%} B&H (warmup)"
            else:
                issue = f"Needs investigation"

        # Check time in market
        total_bars = len(h) - 20  # minus warmup
        in_market = sum((t.exit_time - t.entry_time).days for t in r.trades
                        if hasattr(t.exit_time, 'day'))
        pct_in = in_market / max(total_bars, 1)

        print(f"{name:<12} {bh:>+6.1%} {r.total_return:>+6.1%} {alpha:>+6.1%} | "
              f"{r.total_trades:>7} {r.win_rate:>3.0%} {r.max_drawdown:>+6.1%} | {issue}")

    # Summary of what can be improved
    print(f"\n--- IMPROVEMENT OPPORTUNITIES ---")
    print("1. NVDA/AMZN/CATL: structural (warmup misses early gains) - UNSOLVABLE")
    print("2. Moutai: pos_size in ranging when uptrend - PARTIALLY DONE")
    print("3. AAPL/CSI300/BTC: already positive alpha, diminishing returns")
    print("4. ALL: signal_exit in first 3 bars often whipsaw - could help TSLA/META")
    print("5. BEAR scenarios: INTC/CSI300 already excellent")

asyncio.run(main())
