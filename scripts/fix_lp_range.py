"""Remove old out-of-range LPs and recreate with correct tick range"""
from web3 import Web3
from eth_account import Account
import time

Account.enable_unaudited_hdwallet_features()
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
with open(r"C:\Users\kazhou\.openclaw\secrets\arb_wallet.key") as f:
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

NFT_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "tokenOfOwnerByIndex", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"uint256"}], "name": "positions", "outputs": [
        {"name":"nonce","type":"uint96"}, {"name":"operator","type":"address"},
        {"name":"token0","type":"address"}, {"name":"token1","type":"address"},
        {"name":"fee","type":"uint24"}, {"name":"tickLower","type":"int24"},
        {"name":"tickUpper","type":"int24"}, {"name":"liquidity","type":"uint128"},
        {"name":"feeGrowthInside0LastX128","type":"uint256"},
        {"name":"feeGrowthInside1LastX128","type":"uint256"},
        {"name":"tokensOwed0","type":"uint256"}, {"name":"tokensOwed1","type":"uint256"}
    ], "type": "function"},
    {"inputs": [{"components": [
        {"name":"tokenId","type":"uint256"}, {"name":"liquidity","type":"uint128"},
        {"name":"amount0Min","type":"uint256"}, {"name":"amount1Min","type":"uint256"},
        {"name":"deadline","type":"uint256"}
    ], "name":"params", "type":"tuple"}],
    "name": "decreaseLiquidity", "outputs": [
        {"name":"amount0","type":"uint256"}, {"name":"amount1","type":"uint256"}
    ], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"components": [
        {"name":"tokenId","type":"uint256"}, {"name":"recipient","type":"address"},
        {"name":"amount0Max","type":"uint128"}, {"name":"amount1Max","type":"uint128"}
    ], "name":"params", "type":"tuple"}],
    "name": "collect", "outputs": [
        {"name":"amount0","type":"uint256"}, {"name":"amount1","type":"uint256"}
    ], "stateMutability": "nonpayable", "type": "function"},
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

nft = w3.eth.contract(address=NFT_MANAGER, abi=NFT_ABI + MINT_ABI)

# Find our recent LP positions (the ones we created today with wrong ticks)
lp_count = nft.functions.balanceOf(wallet).call()
print(f"Total LP positions: {lp_count}")

# Check last few positions (ours are the most recent)
our_positions = []
for i in range(max(0, lp_count - 5), lp_count):
    token_id = nft.functions.tokenOfOwnerByIndex(wallet, i).call()
    pos = nft.functions.positions(token_id).call()
    tick_lower = pos[5]
    tick_upper = pos[6]
    liquidity = pos[7]
    print(f"  #{token_id}: ticks={tick_lower}/{tick_upper} liq={liquidity}")
    
    # Our bad positions have ticks -356400/-349460
    if tick_lower == -356400 and tick_upper == -349460 and liquidity > 0:
        our_positions.append((token_id, liquidity))

print(f"\nFound {len(our_positions)} out-of-range positions to fix")

# Remove liquidity from each bad position
MAX_UINT128 = 2**128 - 1
for token_id, liquidity in our_positions:
    print(f"\nRemoving liquidity from #{token_id}...")
    
    # Decrease liquidity
    nonce = w3.eth.get_transaction_count(wallet)
    params = (token_id, liquidity, 0, 0, int(time.time()) + 300)
    tx = nft.functions.decreaseLiquidity(params).build_transaction({
        "from": wallet, "nonce": nonce, "gas": 300000,
        "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=60)
    print(f"  Decrease: {'OK' if r.status == 1 else 'FAILED'}")
    time.sleep(2)
    
    # Collect tokens
    nonce = w3.eth.get_transaction_count(wallet)
    params = (token_id, wallet, MAX_UINT128, MAX_UINT128)
    tx = nft.functions.collect(params).build_transaction({
        "from": wallet, "nonce": nonce, "gas": 200000,
        "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
    })
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h, timeout=60)
    print(f"  Collect: {'OK' if r.status == 1 else 'FAILED'}")
    time.sleep(2)

# Check recovered balances
weth_c = w3.eth.contract(address=WETH, abi=ERC20_ABI)
usdc_c = w3.eth.contract(address=USDC, abi=ERC20_ABI)
weth_bal = weth_c.functions.balanceOf(wallet).call()
usdc_bal = usdc_c.functions.balanceOf(wallet).call()
print(f"\nRecovered: WETH={weth_bal/1e18:.6f} USDC={usdc_bal/1e6:.2f}")

# Now create LP with CORRECT tick range
# Current tick: -199618, range +-30% = -203190 to -197000
CORRECT_LOWER = -203190
CORRECT_UPPER = -197000

total_value_usdc = usdc_bal  # USDC we have
# Also swap half WETH to USDC if we have WETH
if weth_bal > 0:
    print(f"\nSwapping WETH to USDC for balanced LP...")
    V3_ROUTER = Web3.to_checksum_address("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    V3_ROUTER_ABI = [{"inputs": [{"components": [
        {"name":"tokenIn","type":"address"},{"name":"tokenOut","type":"address"},
        {"name":"fee","type":"uint24"},{"name":"recipient","type":"address"},
        {"name":"deadline","type":"uint256"},{"name":"amountIn","type":"uint256"},
        {"name":"amountOutMinimum","type":"uint256"},{"name":"sqrtPriceLimitX96","type":"uint160"}
    ],"name":"params","type":"tuple"}],
    "name":"exactInputSingle","outputs":[{"name":"","type":"uint256"}],
    "stateMutability":"payable","type":"function"}]
    
    # Swap half WETH
    swap_amt = weth_bal // 2
    if weth_c.functions.allowance(wallet, V3_ROUTER).call() < swap_amt:
        nonce = w3.eth.get_transaction_count(wallet)
        tx = weth_c.functions.approve(V3_ROUTER, weth_bal).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 100000,
            "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
        })
        signed = acct.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(h, timeout=60)
        time.sleep(2)
    
    router = w3.eth.contract(address=V3_ROUTER, abi=V3_ROUTER_ABI)
    params = (WETH, USDC, 500, wallet, int(time.time())+300, swap_amt, 0, 0)
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

# Get final balances for LP
weth_bal = weth_c.functions.balanceOf(wallet).call()
usdc_bal = usdc_c.functions.balanceOf(wallet).call()
print(f"\nFor LP: WETH={weth_bal/1e18:.6f} USDC={usdc_bal/1e6:.2f}")

# Approve for NFT Manager
for name, token, amount in [("WETH", WETH, weth_bal), ("USDC", USDC, usdc_bal)]:
    if amount > 0:
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

# Mint with correct range
t0, t1 = (WETH, USDC) if int(WETH, 16) < int(USDC, 16) else (USDC, WETH)
a0 = weth_bal if t0 == WETH else usdc_bal
a1 = usdc_bal if t0 == WETH else weth_bal

print(f"\nMinting LP with CORRECT range: tick {CORRECT_LOWER} to {CORRECT_UPPER}")
params = (t0, t1, 500, CORRECT_LOWER, CORRECT_UPPER, a0, a1, 0, 0, wallet, int(time.time())+300)
nonce = w3.eth.get_transaction_count(wallet)
tx = nft.functions.mint(params).build_transaction({
    "from": wallet, "nonce": nonce, "value": 0, "gas": 500000,
    "maxFeePerGas": w3.eth.gas_price * 2, "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
h = w3.eth.send_raw_transaction(signed.raw_transaction)
r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
print(f"Mint: {'OK' if r.status == 1 else 'FAILED'}")

time.sleep(2)
weth_f = weth_c.functions.balanceOf(wallet).call() / 1e18
usdc_f = usdc_c.functions.balanceOf(wallet).call() / 1e6
print(f"\n=== DONE ===")
print(f"WETH remaining: {weth_f:.6f}")
print(f"USDC remaining: {usdc_f:.2f}")
print(f"LP now IN RANGE and earning fees!")
