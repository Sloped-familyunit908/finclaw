"""Wrap most ETH to WETH, swap half to USDC, add LP"""
from web3 import Web3
from eth_account import Account
import time

Account.enable_unaudited_hdwallet_features()
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
import os
_SECRETS_DIR = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))
with open(os.path.join(_SECRETS_DIR, "arb_wallet.key")) as f:
    acct = Account.from_mnemonic(f.read().strip())

wallet = acct.address
WETH = Web3.to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1")
USDC = Web3.to_checksum_address("0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
V3_ROUTER = Web3.to_checksum_address("0xE592427A0AEce92De3Edee1F18E0157C05861564")
NFT_MANAGER = Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]
WETH_DEPOSIT = [{"constant": False, "inputs": [], "name": "deposit", "outputs": [], "stateMutability": "payable", "type": "function"}]
V3_ROUTER_ABI = [{"inputs": [{"components": [
    {"name": "tokenIn", "type": "address"}, {"name": "tokenOut", "type": "address"},
    {"name": "fee", "type": "uint24"}, {"name": "recipient", "type": "address"},
    {"name": "deadline", "type": "uint256"}, {"name": "amountIn", "type": "uint256"},
    {"name": "amountOutMinimum", "type": "uint256"}, {"name": "sqrtPriceLimitX96", "type": "uint160"}
], "name": "params", "type": "tuple"}],
"name": "exactInputSingle", "outputs": [{"name": "amountOut", "type": "uint256"}],
"stateMutability": "payable", "type": "function"}]
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

weth_c = w3.eth.contract(address=WETH, abi=ERC20_ABI + WETH_DEPOSIT)
usdc_c = w3.eth.contract(address=USDC, abi=ERC20_ABI)

eth_bal = w3.eth.get_balance(wallet)
weth_bal = weth_c.functions.balanceOf(wallet).call()
print(f"ETH: {eth_bal/1e18:.6f} (${eth_bal/1e18*2140:.2f})")
print(f"WETH: {weth_bal/1e18:.6f} (${weth_bal/1e18*2140:.2f})")

# Keep only ~$20 ETH for gas = ~0.0093 ETH
gas_reserve = w3.to_wei(0.0094, 'ether')
wrap_amount = eth_bal - gas_reserve
if wrap_amount <= 0:
    print("Not enough ETH to wrap"); exit()

# Step 1: Wrap ETH
print(f"\nStep 1: Wrap {wrap_amount/1e18:.6f} ETH -> WETH (keeping ${gas_reserve/1e18*2140:.0f} gas)")
nonce = w3.eth.get_transaction_count(wallet)
tx = weth_c.functions.deposit().build_transaction({
    "from": wallet, "nonce": nonce, "value": wrap_amount,
    "gas": 50000, "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
r = w3.eth.wait_for_transaction_receipt(h, timeout=60)
print(f"  Wrap: {'OK' if r.status == 1 else 'FAILED'}")
time.sleep(2)

# Step 2: Swap half WETH to USDC
total_weth = weth_c.functions.balanceOf(wallet).call()
swap_amount = total_weth // 2
print(f"\nStep 2: Swap {swap_amount/1e18:.6f} WETH -> USDC")

allowance = weth_c.functions.allowance(wallet, V3_ROUTER).call()
if allowance < swap_amount:
    nonce = w3.eth.get_transaction_count(wallet)
    tx = weth_c.functions.approve(V3_ROUTER, swap_amount).build_transaction({
        "from": wallet, "nonce": nonce, "gas": 100000,
        "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(h, timeout=60)
    time.sleep(2)

router = w3.eth.contract(address=V3_ROUTER, abi=V3_ROUTER_ABI)
deadline = int(time.time()) + 300
params = (WETH, USDC, 500, wallet, deadline, swap_amount, 0, 0)
nonce = w3.eth.get_transaction_count(wallet)
tx = router.functions.exactInputSingle(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 300000,
    "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
print(f"  Swap: {'OK' if r.status == 1 else 'FAILED'}")
time.sleep(3)

# Step 3: Add LP
weth_for_lp = weth_c.functions.balanceOf(wallet).call()
usdc_for_lp = usdc_c.functions.balanceOf(wallet).call()
print(f"\nStep 3: Add LP - WETH={weth_for_lp/1e18:.6f} USDC={usdc_for_lp/1e6:.2f}")

# Approve
for name, token, amount in [("WETH", WETH, weth_for_lp), ("USDC", USDC, usdc_for_lp)]:
    tc = w3.eth.contract(address=token, abi=ERC20_ABI)
    if tc.functions.allowance(wallet, NFT_MANAGER).call() < amount:
        nonce = w3.eth.get_transaction_count(wallet)
        tx = tc.functions.approve(NFT_MANAGER, amount).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 100000,
            "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        })
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(h, timeout=60)
        time.sleep(2)

if int(WETH, 16) < int(USDC, 16):
    t0, t1, a0, a1 = WETH, USDC, weth_for_lp, usdc_for_lp
else:
    t0, t1, a0, a1 = USDC, WETH, usdc_for_lp, weth_for_lp

nft_m = w3.eth.contract(address=NFT_MANAGER, abi=MINT_ABI)
deadline = int(time.time()) + 300
params = (t0, t1, 500, -356400, -349460, a0, a1, 0, 0, wallet, deadline)
nonce = w3.eth.get_transaction_count(wallet)
tx = nft_m.functions.mint(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 500000,
    "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
print(f"  Mint: {'OK' if r.status == 1 else 'FAILED'}")

time.sleep(2)
eth_final = w3.eth.get_balance(wallet) / 1e18
weth_final = weth_c.functions.balanceOf(wallet).call() / 1e18
usdc_final = usdc_c.functions.balanceOf(wallet).call() / 1e6
print(f"\n=== Final ===")
print(f"ETH: {eth_final:.6f} (${eth_final*2140:.2f}) [gas only]")
print(f"WETH: {weth_final:.6f}")
print(f"USDC: {usdc_final:.2f}")
