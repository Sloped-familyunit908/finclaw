from benchmark_v6 import sim

h = sim(500, 252, 0.80, 0.50, 1395)
# How is B&H calculated in the benchmark?
bh_benchmark = h[-1]['price'] / h[0]['price'] - 1
print(f"B&H from bar 0: {bh_benchmark*100:.1f}%")

bh_warmup = h[-1]['price'] / h[20]['price'] - 1
print(f"B&H from bar 20: {bh_warmup*100:.1f}%")

# Check prices at each bar boundary
for i in [0, 10, 20, 30]:
    print(f"bar {i}: {h[i]['price']:.0f}")
print(f"bar -1: {h[-1]['price']:.0f}")
