import akshare as ak

df = ak.stock_zh_a_spot_em()

# Search
matches = df[df['名称'].str.contains('元捷|源杰|捷科', na=False)]
print("=== Search Results ===")
for _, row in matches.iterrows():
    code = row['代码']
    name = row['名称']
    price = row['最新价']
    change = row['涨跌幅']
    print(f"  {code} {name} {price}元 {change}%")

# Top priced stocks
print("\n=== A股 > 900元 ===")
high = df[df['最新价'] > 900].sort_values('最新价', ascending=False).head(10)
for _, row in high.iterrows():
    code = row['代码']
    name = row['名称']
    price = row['最新价']
    change = row['涨跌幅']
    print(f"  {code} {name} {price}元 {change}%")
