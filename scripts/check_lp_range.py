"""Check current pool price and our LP ranges"""
from web3 import Web3
import math

w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))

# Uniswap V3 WETH-USDC 0.05% pool on Arbitrum
POOL = Web3.to_checksum_address("0xC6962004f452bE9203591991D15f6b388e09E8D0")
POOL_ABI = [
    {"constant": True, "inputs": [], "name": "slot0", "outputs": [
        {"name": "sqrtPriceX96", "type": "uint160"},
        {"name": "tick", "type": "int24"},
        {"name": "observationIndex", "type": "uint16"},
        {"name": "observationCardinality", "type": "uint16"},
        {"name": "observationCardinalityNext", "type": "uint16"},
        {"name": "feeProtocol", "type": "uint8"},
        {"name": "unlocked", "type": "bool"}
    ], "type": "function"},
    {"constant": True, "inputs": [], "name": "token0", "outputs": [{"name":"","type":"address"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "token1", "outputs": [{"name":"","type":"address"}], "type": "function"},
]

pool = w3.eth.contract(address=POOL, abi=POOL_ABI)
slot0 = pool.functions.slot0().call()
current_tick = slot0[1]
token0 = pool.functions.token0().call()
token1 = pool.functions.token1().call()

print(f"Pool: WETH-USDC 0.05%")
print(f"Token0: {token0}")
print(f"Token1: {token1}")
print(f"Current tick: {current_tick}")

# Calculate current price from tick
# price = 1.0001^tick
# But need to account for decimals: WETH=18, USDC=6
# If token0=WETH, token1=USDC: price = 1.0001^tick * 10^(18-6) = price in USDC per WETH
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
if token0.lower() == WETH.lower():
    # token0=WETH, token1=USDC
    # tick represents price of token0 in terms of token1
    # price_usdc_per_weth = 1.0001^tick / 10^(18-6)
    raw_price = 1.0001 ** current_tick
    price = raw_price / 1e12  # adjust for decimal difference
    print(f"ETH price: ${price:.2f}")
else:
    # token0=USDC, token1=WETH
    raw_price = 1.0001 ** current_tick
    price = 1 / (raw_price * 1e12)
    print(f"ETH price: ${price:.2f}")

# Our LP range
our_lower = -356400
our_upper = -349460

if token0.lower() == WETH.lower():
    price_lower = (1.0001 ** our_lower) / 1e12
    price_upper = (1.0001 ** our_upper) / 1e12
else:
    price_upper = 1 / ((1.0001 ** our_lower) * 1e12)
    price_lower = 1 / ((1.0001 ** our_upper) * 1e12)

print(f"\nOur LP range: tick {our_lower} to {our_upper}")
print(f"Our LP price range: ${price_lower:.2f} - ${price_upper:.2f}")
print(f"Current price: ${price:.2f}")

if price < price_lower:
    print(f"STATUS: BELOW RANGE - only USDC side active (not earning optimally)")
elif price > price_upper:
    print(f"STATUS: ABOVE RANGE - only WETH side active (not earning optimally)")
else:
    print(f"STATUS: IN RANGE - both sides active, earning fees!")

# Calculate correct ticks for a good range around current price
# Target: current price +/- 30%
target_low = price * 0.7
target_high = price * 1.3

# Calculate ticks
if token0.lower() == WETH.lower():
    tick_low = int(math.log(target_low * 1e12) / math.log(1.0001))
    tick_high = int(math.log(target_high * 1e12) / math.log(1.0001))
else:
    tick_high = int(math.log(1 / (target_low * 1e12)) / math.log(1.0001))
    tick_low = int(math.log(1 / (target_high * 1e12)) / math.log(1.0001))

# Round to tick spacing (10)
tick_low = (tick_low // 10) * 10
tick_high = (tick_high // 10) * 10

print(f"\nRECOMMENDED range for current price:")
print(f"  Price: ${target_low:.0f} - ${target_high:.0f}")
print(f"  Ticks: {tick_low} to {tick_high}")
print(f"  Current tick: {current_tick}")
print(f"  In range: {tick_low <= current_tick <= tick_high}")
