import sys, time
sys.path.insert(0, r'C:\Users\kazhou\.openclaw\workspace\finclaw')
from src.evolution.unified_evolver import UnifiedEvolver, UnifiedDNA

for n in [10, 30, 50]:
    dna = UnifiedDNA()
    dna.max_stocks = n
    e = UnifiedEvolver(data_dir=r'C:\Users\kazhou\.openclaw\workspace\finclaw\data\a_shares', best_dna=dna)
    data = e.load_elite_pool()
    t = time.time()
    try:
        r = e.backtest(dna, data)
        elapsed = time.time() - t
        ar = r["annual_return"]
        dd = r["max_drawdown"]
        tr = r["total_trades"]
        print(f"n={n}: {elapsed:.1f}s, return={ar}%, dd={dd}%, trades={tr}", flush=True)
    except Exception as ex:
        print(f"n={n}: ERROR {ex}", flush=True)
