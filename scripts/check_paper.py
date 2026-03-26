import json

trades = json.load(open(r'C:\Users\kazhou\.openclaw\workspace\finclaw\data\crypto\paper_trades.json'))
positions = {}
cash = 10000
for t in trades:
    if t['action'] == 'BUY':
        positions[t['symbol']] = {'price': t['price'], 'qty': t['qty'], 'cost': t['cost'], 'time': t['time']}
        cash -= t['cost']
    elif t['action'] == 'SELL':
        if t['symbol'] in positions:
            del positions[t['symbol']]
        cash += t['price'] * t['qty']

print('=== Paper Trading P&L ===')
print(f'Cash remaining: ${cash:.2f}')
print(f'Open positions: {len(positions)}')
for sym, p in positions.items():
    print(f"  {sym}: entry=${p['price']:.4f}, qty={p['qty']:.2f}, cost=${p['cost']:.2f}, opened={p['time']}")

# Estimate current value (using entry prices as proxy since we can't fetch live)
total_invested = sum(p['cost'] for p in positions.values())
print(f'Total invested in positions: ${total_invested:.2f}')
print(f'Portfolio value (at entry): ${cash + total_invested:.2f}')
