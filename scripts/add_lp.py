"""
Add liquidity to Uniswap V3 WETH-USDC pool on Arbitrum.
Uses NonfungiblePositionManager to mint a new position.
"""
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
# Uniswap V3 NonfungiblePositionManager on Arbitrum
NFT_MANAGER = Web3.to_checksum_address("0xC36442b4a4522E871399CD717aBDD847Ab11FE88")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

# Mint new position ABI
MINT_ABI = [{
    "inputs": [{"components": [
        {"name": "token0", "type": "address"},
        {"name": "token1", "type": "address"},
        {"name": "fee", "type": "uint24"},
        {"name": "tickLower", "type": "int24"},
        {"name": "tickUpper", "type": "int24"},
        {"name": "amount0Desired", "type": "uint256"},
        {"name": "amount1Desired", "type": "uint256"},
        {"name": "amount0Min", "type": "uint256"},
        {"name": "amount1Min", "type": "uint256"},
        {"name": "recipient", "type": "address"},
        {"name": "deadline", "type": "uint256"}
    ], "name": "params", "type": "tuple"}],
    "name": "mint",
    "outputs": [
        {"name": "tokenId", "type": "uint256"},
        {"name": "liquidity", "type": "uint128"},
        {"name": "amount0", "type": "uint256"},
        {"name": "amount1", "type": "uint256"}
    ],
    "stateMutability": "payable",
    "type": "function"
}]

weth_c = w3.eth.contract(address=WETH, abi=ERC20_ABI)
usdc_c = w3.eth.contract(address=USDC, abi=ERC20_ABI)

weth_bal = weth_c.functions.balanceOf(wallet).call()
usdc_bal = usdc_c.functions.balanceOf(wallet).call()
print(f"WETH: {weth_bal/1e18:.6f} (${weth_bal/1e18*2140:.2f})")
print(f"USDC: {usdc_bal/1e6:.2f}")

# Determine token0/token1 order (Uniswap requires token0 < token1 by address)
if int(USDC, 16) < int(WETH, 16):
    token0, token1 = USDC, WETH
    amount0 = usdc_bal
    amount1 = weth_bal
    print(f"\ntoken0=USDC, token1=WETH")
else:
    token0, token1 = WETH, USDC
    amount0 = weth_bal
    amount1 = usdc_bal
    print(f"\ntoken0=WETH, token1=USDC")

# Approve both tokens for NFT Manager
for name, token, amount in [("WETH", WETH, weth_bal), ("USDC", USDC, usdc_bal)]:
    tc = w3.eth.contract(address=token, abi=ERC20_ABI)
    allowance = tc.functions.allowance(wallet, NFT_MANAGER).call()
    if allowance < amount:
        print(f"Approving {name}...")
        nonce = w3.eth.get_transaction_count(wallet)
        tx = tc.functions.approve(NFT_MANAGER, amount).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 100000,
            "maxFeePerGas": w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        })
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        r = w3.eth.wait_for_transaction_receipt(h, timeout=60)
        status = "OK" if r.status == 1 else "FAILED"
        print(f"  {name} approve: {status}")
        time.sleep(2)
    else:
        print(f"{name} already approved")

# Wide range LP: current price ~$2140
# Use ticks for range $1500 - $3000 (wide range, less IL, less maintenance)
# For USDC/WETH 0.05% pool:
# tick = log(price) / log(1.0001)
# USDC is 6 decimals, WETH is 18 decimals
# If token0=USDC: price = USDC_per_WETH / (10^6 / 10^18) = price * 10^12
# tick at $1500: log(1500 * 10^12) / log(1.0001) ≈ 200,000 area
# Let me calculate properly
import math

# For USDC(6 dec)/WETH(18 dec) pool:
# sqrtPriceX96 = sqrt(price_token1_in_token0 * 10^(decimals0-decimals1)) * 2^96
# price at tick = 1.0001^tick * 10^(decimals1-decimals0)
# tick = log(price / 10^(decimals1-decimals0)) / log(1.0001)

if int(USDC, 16) < int(WETH, 16):
    # token0=USDC(6dec), token1=WETH(18dec)
    # price in pool = amount0/amount1 = USDC_per_WETH * 10^(18-6) = price * 10^12
    # tick = log(price * 10^12) / log(1.0001)
    tick_1500 = int(math.log(1500 * 1e12) / math.log(1.0001))
    tick_3000 = int(math.log(3000 * 1e12) / math.log(1.0001))
else:
    # token0=WETH(18dec), token1=USDC(6dec)
    # price = USDC_per_WETH but inverted: amount1/amount0
    # tick = log(1/price * 10^(6-18)) / log(1.0001) = log(10^(-12)/price) / log(1.0001)
    tick_3000 = int(math.log(1e-12 / 3000) / math.log(1.0001))  # lower tick (lower price = more WETH)
    tick_1500 = int(math.log(1e-12 / 1500) / math.log(1.0001))  # upper tick

# Round to nearest tick spacing (10 for 0.05% pools)
tick_spacing = 10
tick_lower = (min(tick_1500, tick_3000) // tick_spacing) * tick_spacing
tick_upper = (max(tick_1500, tick_3000) // tick_spacing) * tick_spacing

print(f"\nLP Range: tick {tick_lower} to {tick_upper}")
print(f"Approx price range: $1,500 - $3,000")

# Mint position
nft_manager = w3.eth.contract(address=NFT_MANAGER, abi=MINT_ABI)
deadline = int(time.time()) + 300

params = (
    token0,
    token1,
    500,  # 0.05% fee
    tick_lower,
    tick_upper,
    amount0,
    amount1,
    0,  # amount0Min (accept any for small amounts)
    0,  # amount1Min
    wallet,
    deadline,
)

print(f"\nMinting LP position...")
nonce = w3.eth.get_transaction_count(wallet)
tx = nft_manager.functions.mint(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 500000,
    "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Mint tx: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
status = "OK" if receipt.status == 1 else "FAILED"
print(f"Mint: {status} | Gas: {receipt.gasUsed}")

if receipt.status == 1:
    # Check remaining balances
    time.sleep(2)
    weth_after = weth_c.functions.balanceOf(wallet).call()
    usdc_after = usdc_c.functions.balanceOf(wallet).call()
    print(f"\nRemaining WETH: {weth_after/1e18:.6f}")
    print(f"Remaining USDC: {usdc_after/1e6:.2f}")
    print(f"LP Position created! Earning fees from WETH-USDC trades.")
