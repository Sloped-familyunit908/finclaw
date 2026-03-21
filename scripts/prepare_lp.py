"""
Step 1: Convert half WETH to USDC for LP
Step 2: Add liquidity to Uniswap V3 ETH-USDC pool on Arbitrum
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

TOKENS = {
    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
}
V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

V3_ROUTER_ABI = [{
    "inputs": [{"components": [
        {"name": "tokenIn", "type": "address"},
        {"name": "tokenOut", "type": "address"},
        {"name": "fee", "type": "uint24"},
        {"name": "recipient", "type": "address"},
        {"name": "deadline", "type": "uint256"},
        {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMinimum", "type": "uint256"},
        {"name": "sqrtPriceLimitX96", "type": "uint160"}
    ], "name": "params", "type": "tuple"}],
    "name": "exactInputSingle",
    "outputs": [{"name": "amountOut", "type": "uint256"}],
    "stateMutability": "payable",
    "type": "function"
}]

wallet = acct.address
weth_c = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WETH"]), abi=ERC20_ABI)
usdc_c = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["USDC"]), abi=ERC20_ABI)

# Current balances
weth_bal = weth_c.functions.balanceOf(wallet).call()
usdc_bal = usdc_c.functions.balanceOf(wallet).call()
eth_bal = w3.eth.get_balance(wallet)

print(f"=== Current Balances ===")
print(f"ETH:  {eth_bal/1e18:.6f} (${eth_bal/1e18 * 2140:.2f})")
print(f"WETH: {weth_bal/1e18:.6f} (${weth_bal/1e18 * 2140:.2f})")
print(f"USDC: {usdc_bal/1e6:.2f}")

# Swap half WETH to USDC
swap_amount = weth_bal // 2  # half of WETH
print(f"\n=== Swapping {swap_amount/1e18:.6f} WETH -> USDC ===")

# Approve WETH for router
allowance = weth_c.functions.allowance(wallet, Web3.to_checksum_address(V3_ROUTER)).call()
if allowance < swap_amount:
    print("Approving WETH...")
    nonce = w3.eth.get_transaction_count(wallet)
    tx = weth_c.functions.approve(
        Web3.to_checksum_address(V3_ROUTER), swap_amount
    ).build_transaction({
        "from": wallet, "nonce": nonce, "gas": 100000,
        "maxFeePerGas": w3.eth.gas_price * 2,
        "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    status = "OK" if receipt.status == 1 else "FAILED"
    print(f"  Approve: {status}")
    time.sleep(2)

# Swap WETH -> USDC (0.05% fee pool)
router = w3.eth.contract(address=Web3.to_checksum_address(V3_ROUTER), abi=V3_ROUTER_ABI)
deadline = int(time.time()) + 300

params = (
    Web3.to_checksum_address(TOKENS["WETH"]),
    Web3.to_checksum_address(TOKENS["USDC"]),
    500,  # 0.05% fee
    wallet,
    deadline,
    swap_amount,
    0,  # min out
    0,  # no price limit
)

nonce = w3.eth.get_transaction_count(wallet)
tx = router.functions.exactInputSingle(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 300000,
    "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Swap tx: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
status = "OK" if receipt.status == 1 else "FAILED"
print(f"Swap: {status} | Gas: {receipt.gasUsed}")

time.sleep(3)

# After balances
weth_after = weth_c.functions.balanceOf(wallet).call()
usdc_after = usdc_c.functions.balanceOf(wallet).call()
print(f"\n=== After Swap ===")
print(f"WETH: {weth_after/1e18:.6f} (${weth_after/1e18 * 2140:.2f})")
print(f"USDC: {usdc_after/1e6:.2f}")
