import json, os
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_PROJECT_DIR, 'evolution_results', 'latest.json')) as f:
    d = json.load(f)
r = d["results"][0]
print(f"Trades: {r['total_trades']}")
print(f"Profit factor: {r['profit_factor']:.2f}")
dna = r["dna"]
for k, v in dna.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")
