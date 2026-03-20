from web3 import Web3
wallet = Web3.to_checksum_address('0xe62aa01e03a55fb81d70c647b444178207a07afe')

chains = {
    "ETH Mainnet": ("https://eth.llamarpc.com", 18, 2140, "ETH"),
    "BNB Chain": ("https://bsc-dataseed.binance.org", 18, 644, "BNB"),
    "Blast": ("https://rpc.blast.io", 18, 2140, "ETH"),
    "Arbitrum": ("https://arb1.arbitrum.io/rpc", 18, 2140, "ETH"),
}

for name, (rpc, dec, price, symbol) in chains.items():
    try:
        w3 = Web3(Web3.HTTPProvider(rpc))
        bal = w3.eth.get_balance(wallet) / 10**dec
        usd = bal * price
        print(f"{name}: {bal:.6f} {symbol} (${usd:.2f})")
    except Exception as e:
        print(f"{name}: error - {e}")
