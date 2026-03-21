import sys, time, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.evolution.unified_evolver import UnifiedEvolver, UnifiedDNA

_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

dna = UnifiedDNA()
dna.max_stocks = 50
dna.w_cn_scanner = 0.6
dna.w_technical = 0.4
dna.w_ml = 0.0

print('Creating evolver...', flush=True)
e = UnifiedEvolver(data_dir=os.path.join(_PROJECT_DIR, 'data', 'a_shares'), best_dna=dna)

print('Loading pool...', flush=True)
t = time.time()
data = e.load_elite_pool()
print(f'Loaded {len(data)} in {time.time()-t:.1f}s', flush=True)

print('Backtesting 1 DNA...', flush=True)
try:
    t = time.time()
    result = e.backtest(dna, data)
    elapsed = time.time() - t
    print(f'Backtest done in {elapsed:.1f}s', flush=True)
    ar = result["annual_return"]
    dd = result["max_drawdown"]
    tr = result["total_trades"]
    wr = result["win_rate"]
    print(f'Return: {ar}%, DD: {dd}%, Trades: {tr}, WinRate: {wr}%')
    print('SUCCESS')
except Exception as ex:
    import traceback
    traceback.print_exc()
    print(f'ERROR: {ex}')
