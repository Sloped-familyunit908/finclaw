import asyncio, random, math
from datetime import datetime, timedelta
from agents.backtester_v2 import BacktesterV2, Position
from agents.signal_engine import SignalEngine, MarketRegime

def sim(start, days, ret, vol, seed=42, jp=0.02, js=0.04):
    rng = random.Random(seed)
    dt = 1/252; prices = [start]
    for _ in range(days-1):
        dW = rng.gauss(0, math.sqrt(dt))
        j = rng.gauss(0,js) if rng.random() < jp else 0
        prices.append(max(prices[-1] * math.exp((ret-0.5*vol**2)*dt + vol*dW + j), 0.01))
    base = datetime(2025,3,1)
    return [{'date': base+timedelta(days=i), 'price': p, 'volume': abs(rng.gauss(p*1e6,p*5e5))} for i,p in enumerate(prices)]

async def experiment():
    """What if we NEVER sell on signal in bull? Only trailing stop."""
    
    for name, start, ret, vol, seed in [('NVDA', 500, 0.80, 0.50, 1395), ('CATL', 220, 0.55, 0.45, 1323)]:
        h = sim(start, 252, ret, vol, seed)
        prices = [x['price'] for x in h]
        bh = h[-1]['price']/h[0]['price']-1
        
        # Standard run
        bt = BacktesterV2(initial_capital=10000)
        r1 = await bt.run(name, 'Standard', h)
        
        # Manual "buy and hold with trailing" - buy first signal, only exit on trailing stop
        se = SignalEngine()
        capital = 10000
        position = None
        trades = []
        
        for i in range(50, len(h)):
            price = h[i]['price']
            
            if position:
                position.update_trailing(price)
                # Only exit on stop_loss (trailing)
                reason = position.should_exit(price)
                if reason == "stop_loss":
                    pnl = (price / position.entry_price - 1)
                    trades.append(pnl)
                    capital *= (1 + pnl)
                    position = None
            
            if not position:
                sig = se.generate_signal(prices[:i+1])
                if sig.signal in ("buy", "strong_buy"):
                    position = Position(
                        asset=name, entry_price=price, entry_time=datetime.now(),
                        quantity=1, capital_used=capital,
                        stop_loss=sig.stop_loss, take_profit=price*10,
                        trailing_stop_pct=sig.trailing_stop_pct,
                        highest_since_entry=price,
                        signal_confidence=sig.confidence,
                        regime_at_entry=sig.regime,
                    )
        
        if position:
            pnl = (prices[-1] / position.entry_price - 1)
            trades.append(pnl)
            capital *= (1 + pnl)
        
        manual_ret = capital / 10000 - 1
        wr = sum(1 for t in trades if t > 0) / max(len(trades), 1)
        
        print(f"{name}: B&H={bh:+.1%}")
        print(f"  Standard:  {r1.total_return:+.1%} alpha={r1.alpha:+.1%} {r1.total_trades}t WR={r1.win_rate:.0%}")
        print(f"  No-signal: {manual_ret:+.1%} alpha={manual_ret-bh:+.1%} {len(trades)}t WR={wr:.0%}")
        print()

asyncio.run(experiment())
