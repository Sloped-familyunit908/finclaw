"""Run unified evolution with small elite pool (fast enough to evolve)."""
import sys, time, json, os
sys.path.insert(0, r'C:\Users\kazhou\.openclaw\workspace\finclaw')
from src.evolution.unified_evolver import UnifiedEvolver, UnifiedDNA
import copy, random, math

# Start from best known DNA
dna = UnifiedDNA()
dna.max_stocks = 15  # small but fast
dna.w_cn_scanner = 0.6
dna.w_technical = 0.4
dna.w_ml = 0.0

print("Loading data...", flush=True)
e = UnifiedEvolver(data_dir=r'C:\Users\kazhou\.openclaw\workspace\finclaw\data\a_shares', best_dna=dna)
data = e.load_elite_pool()
print(f"Pool: {len(data)} stocks", flush=True)

# Manual evolution loop (faster than built-in evolve which reloads data)
GENERATIONS = 30
POPULATION = 10
ELITE = 3

# Evaluate initial DNA
print("Evaluating initial DNA...", flush=True)
best_result = e.backtest(dna, data)
best_dna = dna
best_fitness = best_result["fitness"]
print(f"Initial: return={best_result['annual_return']:.0f}% dd={best_result['max_drawdown']:.0f}% fitness={best_fitness:.0f}", flush=True)

results_dir = r'C:\Users\kazhou\.openclaw\workspace\finclaw\evolution_results'
os.makedirs(results_dir, exist_ok=True)

top5 = [(best_fitness, best_result, dna)]

for gen in range(GENERATIONS):
    t0 = time.time()
    
    # Generate mutations from best
    candidates = [e.mutate(best_dna) for _ in range(POPULATION)]
    
    # Evaluate all
    gen_results = []
    for cdna in candidates:
        try:
            r = e.backtest(cdna, data)
            gen_results.append((r["fitness"], r, cdna))
        except:
            pass
    
    if gen_results:
        gen_results.sort(key=lambda x: -x[0])
        
        # Update best
        if gen_results[0][0] > best_fitness:
            best_fitness = gen_results[0][0]
            best_result = gen_results[0][1]
            best_dna = gen_results[0][2]
        
        # Update top5
        for item in gen_results[:ELITE]:
            top5.append(item)
        top5.sort(key=lambda x: -x[0])
        top5 = top5[:5]
        
        r = gen_results[0][1]
        elapsed = time.time() - t0
        print(f"Gen {gen:3d} | fit={r['fitness']:7.0f} | ret={r['annual_return']:+7.0f}% | dd={r['max_drawdown']:5.1f}% | wr={r['win_rate']:4.0f}% | trades={r['total_trades']:3d} | {elapsed:.0f}s", flush=True)

# Save results
print(f"\n{'='*60}", flush=True)
print(f"UNIFIED EVOLUTION COMPLETE", flush=True)
print(f"Best fitness: {best_fitness:.0f}", flush=True)
print(f"Best return: {best_result['annual_return']:.0f}%", flush=True)
print(f"Best drawdown: {best_result['max_drawdown']:.0f}%", flush=True)

print(f"\nTOP 5:", flush=True)
for i, (f, r, d) in enumerate(top5):
    print(f"  #{i+1} return={r['annual_return']:+.0f}% dd={r['max_drawdown']:.0f}% wr={r['win_rate']:.0f}% trades={r['total_trades']} fitness={f:.0f}", flush=True)

# Save
with open(os.path.join(results_dir, 'unified_best.json'), 'w') as f:
    json.dump({"top5": [{"fitness": t[0], "result": t[1]} for t in top5]}, f, indent=2)
print("Saved to unified_best.json", flush=True)
