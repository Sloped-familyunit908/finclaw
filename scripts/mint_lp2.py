"""Add WETH+USDC to Uniswap V3 LP"""
from web3 import Web3
from eth_account import Account
import time, math

Account.enable_unaudited_hdwallet_features()
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
import os
_SECRETS_DIR = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))
with open(os.path.join(_SECRETS_DIR, "arb_wallet.key")) as f:
    acct = Account.from_mnemonic(f.read().strip())

wallet = acct.address
WETH = Web3.to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
USDC = Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
NFT_MANAGER = Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

MINT_ABI = [{"inputs": [{"components": [
    {"name": "token0", "type": "address"}, {"name": "token1", "type": "address"},
    {"name": "fee", "type": "uint24"}, {"name": "tickLower", "type": "int24"},
    {"name": "tickUpper", "type": "int24"}, {"name": "amount0Desired", "type": "uint256"},
    {"name": "amount1Desired", "type": "uint256"}, {"name": "amount0Min", "type": "uint256"},
    {"name": "amount1Min", "type": "uint256"}, {"name": "recipient", "type": "address"},
    {"name": "deadline", "type": "uint256"}
], "name": "params", "type": "tuple"}],
"name": "mint", "outputs": [
    {"name": "tokenId", "type": "uint256"}, {"name": "liquidity", "type": "uint128"},
    {"name": "amount0", "type": "uint256"}, {"name": "amount1", "type": "uint256"}
], "stateMutability": "payable", "type": "function"}]

weth_c = w3.eth.contract(address=WETH, abi=ERC20_ABI)
usdc_c = w3.eth.contract(address=USDC, abi=ERC20_ABI)

weth_bal = weth_c.functions.balanceOf(wallet).call()
usdc_bal = usdc_c.functions.balanceOf(wallet).call()
print(f"WETH: {weth_bal/1e18:.6f} (${weth_bal/1e18*2140:.2f})")
print(f"USDC: {usdc_bal/1e6:.2f}")

# token0/token1 order
if int(WETH, 16) < int(USDC, 16):
    token0, token1, amount0, amount1 = WETH, USDC, weth_bal, usdc_bal
else:
    token0, token1, amount0, amount1 = USDC, WETH, usdc_bal, weth_bal

# Approve both
for name, token, amount in [("WETH", WETH, weth_bal), ("USDC", USDC, usdc_bal)]:
    tc = w3.eth.contract(address=token, abi=ERC20_ABI)
    if tc.functions.allowance(wallet, NFT_MANAGER).call() < amount:
        nonce = w3.eth.get_transaction_count(wallet)
        tx = tc.functions.approve(NFT_MANAGER, amount).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 100000,
            "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        })
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        r = w3.eth.wait_for_transaction_receipt(h, timeout=60)
        print(f"Approve {name}: {'OK' if r.status == 1 else 'FAILED'}")
        time.sleep(2)

# Wide range: $1500-$3000
tick_spacing = 10
tick_lower = -356400
tick_upper = -349460

print(f"\nMinting LP: tick {tick_lower} to {tick_upper}")

nft_manager = w3.eth.contract(address=NFT_MANAGER, abi=MINT_ABI)
deadline = int(time.time()) + 300
params = (token0, token1, 500, tick_lower, tick_upper, amount0, amount1, 0, 0, wallet, deadline)

nonce = w3.eth.get_transaction_count(wallet)
tx = nft_manager.functions.mint(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 500000,
    "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Mint tx: {h.hex()}")
r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
status = "OK" if r.status == 1 else "FAILED"
print(f"Mint: {status} | Gas: {r.gasUsed}")

time.sleep(2)
weth_after = weth_c.functions.balanceOf(wallet).call() / 1e18
usdc_after = usdc_c.functions.balanceOf(wallet).call() / 1e6
print(f"\nAfter: WETH={weth_after:.6f} USDC={usdc_after:.2f}")
print(f"Done! LP position added.")
