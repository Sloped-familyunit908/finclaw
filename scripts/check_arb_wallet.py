from web3 import Web3

w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
wallet = Web3.to_checksum_address('0xe62aa01e03a55fb81d70c647b444178207a07afe')

bal_abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"}]

tokens = {
    "ETH": None,
    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
    "AICODE": "0x2823f231B8b7121c4bA6B6c0cEEF37b6a5bDa547",
}

print("=== ARB Chain Wallet Status ===")
eth_bal = w3.eth.get_balance(wallet) / 1e18
print(f"ETH: {eth_bal:.6f} (${eth_bal * 2140:.2f})")

for name, addr in tokens.items():
    if addr is None:
        continue
    try:
        c = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=bal_abi)
        bal = c.functions.balanceOf(wallet).call()
        if name == "USDC":
            human = bal / 1e6
        else:
            human = bal / 1e18
        if human > 0.001:
            print(f"{name}: {human:.6f}" + (f" (${human:.2f})" if name in ("USDC","DAI") else ""))
    except:
        pass

# Check Uniswap V3 NFT positions
nft_manager = Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")
nft_abi = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "tokenOfOwnerByIndex", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]
try:
    nft = w3.eth.contract(address=nft_manager, abi=nft_abi)
    lp_count = nft.functions.balanceOf(wallet).call()
    print(f"\nUniswap V3 LP positions: {lp_count}")
    for i in range(lp_count):
        token_id = nft.functions.tokenOfOwnerByIndex(wallet, i).call()
        print(f"  Position #{token_id}")
except Exception as e:
    print(f"LP check: {e}")
