from web3 import Web3

arb = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org'))
w = Web3.to_checksum_address('0xe62aa01e03a55fb81d70c647b444178207a07afe')

eth_price = 2140
bnb_price = 644

# ARB balances
eth = arb.eth.get_balance(w) / 1e18
bal_abi = [{"constant":True,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
weth_c = arb.eth.contract(address=Web3.to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"), abi=bal_abi)
weth = weth_c.functions.balanceOf(w).call() / 1e18
usdc_c = arb.eth.contract(address=Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831"), abi=bal_abi)
usdc = usdc_c.functions.balanceOf(w).call() / 1e6

# NFT count (LP positions)
nft_abi = [{"constant":True,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
nft = arb.eth.contract(address=Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88"), abi=nft_abi)
lp_count = nft.functions.balanceOf(w).call()

print("=== ARB Chain ===")
print(f"  ETH: {eth:.4f} (${eth*eth_price:.0f}) [gas]")
print(f"  WETH: {weth:.4f} (${weth*eth_price:.0f})")
print(f"  USDC: {usdc:.2f}")
print(f"  LP positions: {lp_count}")

# BSC
bnb = bsc.eth.get_balance(w) / 1e18
print(f"\n=== BSC Chain ===")
print(f"  BNB: {bnb:.4f} (${bnb*bnb_price:.0f}) [gas]")

# Estimate LP value (we put in ~$163 USDC + ~$210 BNB-USDT)
print(f"\n=== Estimated Total ===")
wallet_value = eth*eth_price + weth*eth_price + usdc + bnb*bnb_price
lp_estimate = 163 + 210  # approximate LP value
print(f"  Wallet: ${wallet_value:.0f}")
print(f"  LP (estimated): ~${lp_estimate}")
print(f"  Total: ~${wallet_value + lp_estimate:.0f}")
