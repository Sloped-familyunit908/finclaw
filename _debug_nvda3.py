from benchmark_v6 import sim

h = sim(500, 252, 0.80, 0.50, 1395)
print(f"bar 0: {h[0]['price']:.0f}")
print(f"bar 20: {h[20]['price']:.0f}")
print(f"bar -1: {h[-1]['price']:.0f}")
bh = h[-1]['price'] / h[20]['price'] - 1
print(f"bh from bar 20: {bh*100:.1f}%")
# Our return: enter at bar 20 price + slippage, exit at bar -1 - slippage
entry = h[20]['price'] * 1.0005
exit_p = h[-1]['price'] * 0.9995
trade_return = exit_p / entry - 1
print(f"trade return: {trade_return*100:.1f}%")
print(f"at 90% invested: {0.9*trade_return*100:.1f}%")
print(f"at 95% invested: {0.95*trade_return*100:.1f}%")
print(f"at 100% invested: {trade_return*100:.1f}%")
