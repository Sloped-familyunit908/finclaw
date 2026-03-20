import json, urllib.request

url = 'https://yields.llama.fi/pools'
data = json.loads(urllib.request.urlopen(url).read())['data']

arb = [p for p in data if p.get('chain') == 'Arbitrum' and p.get('tvlUsd', 0) > 1_000_000 and p.get('apy', 0) > 5]
arb.sort(key=lambda x: -x.get('apy', 0))

print("=" * 90)
print(f"{'Protocol':<20} {'Pool':<25} {'APY%':>7} {'TVL($M)':>8} {'IL':>4} {'Stable':>6}")
print("=" * 90)
for p in arb[:25]:
    il = p.get('ilRisk', '?')
    stb = 'Yes' if p.get('stablecoin') else 'No'
    sym = p.get('symbol', '?')[:24]
    proj = p.get('project', '?')[:19]
    apy = p.get('apy', 0)
    tvl = p.get('tvlUsd', 0) / 1e6
    print(f"{proj:<20} {sym:<25} {apy:>7.2f} {tvl:>8.1f} {il:>4} {stb:>6}")
