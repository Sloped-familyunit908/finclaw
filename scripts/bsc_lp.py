"""Swap half BNB to USDT and add PancakeSwap V2 LP on BSC"""
from web3 import Web3
from eth_account import Account
import time

Account.enable_unaudited_hdwallet_features()
bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org'))
import os
_SECRETS_DIR = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))
with open(os.path.join(_SECRETS_DIR, "arb_wallet.key")) as f:
    acct = Account.from_mnemonic(f.read().strip())

wallet = acct.address
WBNB = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
USDT = Web3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")
PANCAKE_ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

ROUTER_ABI = [
    {
        "inputs": [
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"name": "token", "type": "address"},
            {"name": "amountTokenDesired", "type": "uint256"},
            {"name": "amountTokenMin", "type": "uint256"},
            {"name": "amountETHMin", "type": "uint256"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidityETH",
        "outputs": [
            {"name": "amountToken", "type": "uint256"},
            {"name": "amountETH", "type": "uint256"},
            {"name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
]

router = bsc.eth.contract(address=PANCAKE_ROUTER, abi=ROUTER_ABI)
usdt_c = bsc.eth.contract(address=USDT, abi=ERC20_ABI)

bnb_bal = bsc.eth.get_balance(wallet)
print(f"BNB: {bnb_bal/1e18:.6f} (${bnb_bal/1e18*644:.2f})")

# Keep 0.01 BNB for gas, use 40% for swap (so we have BNB+USDT for LP)
gas_reserve = bsc.to_wei(0.01, "ether")
available = bnb_bal - gas_reserve
swap_amount = available * 45 // 100  # 45% to USDT, keep 55% BNB for LP pair
lp_bnb = available - swap_amount

print(f"Swapping {swap_amount/1e18:.6f} BNB -> USDT")
print(f"Keeping {lp_bnb/1e18:.6f} BNB for LP")

# Step 1: Swap BNB -> USDT
nonce = bsc.eth.get_transaction_count(wallet)
deadline = int(time.time()) + 300

tx = router.functions.swapExactETHForTokens(
    0,  # amountOutMin
    [WBNB, USDT],
    wallet,
    deadline
).build_transaction({
    "from": wallet, "nonce": nonce, "value": swap_amount,
    "gas": 200000, "gasPrice": bsc.to_wei(3, "gwei"),
})
signed = acct.sign_transaction(tx)
h = bsc.eth.send_raw_transaction(signed.raw_transaction)
r = bsc.eth.wait_for_transaction_receipt(h, timeout=60)
status = "OK" if r.status == 1 else "FAILED"
print(f"Swap: {status} | Gas: {r.gasUsed}")

time.sleep(3)

usdt_bal = usdt_c.functions.balanceOf(wallet).call()
bnb_after_swap = bsc.eth.get_balance(wallet)
print(f"\nAfter swap:")
print(f"BNB: {bnb_after_swap/1e18:.6f}")
print(f"USDT: {usdt_bal/1e18:.2f}")

# Step 2: Approve USDT for router
allowance = usdt_c.functions.allowance(wallet, PANCAKE_ROUTER).call()
if allowance < usdt_bal:
    print("\nApproving USDT...")
    nonce = bsc.eth.get_transaction_count(wallet)
    tx = usdt_c.functions.approve(PANCAKE_ROUTER, usdt_bal).build_transaction({
        "from": wallet, "nonce": nonce, "gas": 100000,
        "gasPrice": bsc.to_wei(3, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    h = bsc.eth.send_raw_transaction(signed.raw_transaction)
    r = bsc.eth.wait_for_transaction_receipt(h, timeout=60)
    status = "OK" if r.status == 1 else "FAILED"
    print(f"Approve: {status}")
    time.sleep(2)

# Step 3: Add liquidity BNB + USDT
# Use the USDT we got and matching BNB amount
lp_bnb_amount = bnb_after_swap - gas_reserve - bsc.to_wei(0.01, "ether")  # extra gas buffer

print(f"\nAdding liquidity: {usdt_bal/1e18:.2f} USDT + {lp_bnb_amount/1e18:.6f} BNB")

nonce = bsc.eth.get_transaction_count(wallet)
deadline = int(time.time()) + 300

tx = router.functions.addLiquidityETH(
    USDT,           # token
    usdt_bal,       # amountTokenDesired
    0,              # amountTokenMin (accept any for small amounts)
    0,              # amountETHMin
    wallet,         # to
    deadline,       # deadline
).build_transaction({
    "from": wallet, "nonce": nonce, "value": lp_bnb_amount,
    "gas": 300000, "gasPrice": bsc.to_wei(3, "gwei"),
})
signed = acct.sign_transaction(tx)
h = bsc.eth.send_raw_transaction(signed.raw_transaction)
print(f"AddLiquidity tx: {h.hex()}")
r = bsc.eth.wait_for_transaction_receipt(h, timeout=120)
status = "OK" if r.status == 1 else "FAILED"
print(f"AddLiquidity: {status} | Gas: {r.gasUsed}")

time.sleep(2)

# Final state
bnb_final = bsc.eth.get_balance(wallet) / 1e18
usdt_final = usdt_c.functions.balanceOf(wallet).call() / 1e18

# Check LP token balance
pancake_pair = Web3.to_checksum_address("0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE")  # BNB-USDT pair
try:
    lp_c = bsc.eth.contract(address=pancake_pair, abi=ERC20_ABI)
    lp_bal = lp_c.functions.balanceOf(wallet).call() / 1e18
    print(f"\nLP token balance: {lp_bal:.10f}")
except:
    print("\nLP token: checking...")

print(f"\n=== Final Balances ===")
print(f"BNB: {bnb_final:.6f} (${bnb_final*644:.2f}) [gas reserve]")
print(f"USDT: {usdt_final:.2f}")
print(f"LP: BNB-USDT PancakeSwap V2")
print(f"Done!")
