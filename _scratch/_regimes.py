"""Check regime distribution per scenario."""
import asyncio
from agents.signal_engine_v6 import SignalEngineV6, MarketRegime
from benchmark_v6 import sim

scenarios = [
    ("AAPL",  sim(180, 252, 0.15, 0.25, 1002)),
    ("TSLA",  sim(250, 252, 0.40, 0.65, 1525)),
    ("AMZN",  sim(180, 252, 0.30, 0.35, 1628)),
]

for name, h in scenarios:
    eng = SignalEngineV6()
    prices = [b["price"] for b in h]
    regime_counts = {}
    for i in range(20, len(prices)):
        sig = eng.generate_signal(prices[:i+1])
        r = sig.regime.value
        regime_counts[r] = regime_counts.get(r, 0) + 1
    total = sum(regime_counts.values())
    print(f"\n{name} regime distribution ({total} bars from warmup):")
    for r, c in sorted(regime_counts.items(), key=lambda x: -x[1]):
        print(f"  {r}: {c} ({c/total*100:.0f}%)")
