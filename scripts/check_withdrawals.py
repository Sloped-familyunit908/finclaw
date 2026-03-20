"""
Check all Camelot/xGRAIL positions and find withdrawal methods.
"""
from web3 import Web3
from eth_account import Account
import time

Account.enable_unaudited_hdwallet_features()
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
with open(r"C:\Users\kazhou\.openclaw\secrets\arb_wallet.key") as f:
    acct = Account.from_mnemonic(f.read().strip())

wallet = acct.address

# ========== xGRAIL ==========
xgrail_addr = Web3.to_checksum_address('0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b')

# Check xGRAIL functions for withdrawal
xgrail_funcs = [
    ('balanceOf', [{"name":"","type":"address"}], [{"name":"","type":"uint256"}]),
    ('getUsageAllocations', [{"name":"","type":"address"}], [{"name":"","type":"uint256"}]),
    ('minRedeemDuration', [], [{"name":"","type":"uint256"}]),
    ('maxRedeemDuration', [], [{"name":"","type":"uint256"}]),
    ('getUserRedeemsLength', [{"name":"","type":"address"}], [{"name":"","type":"uint256"}]),
    ('getUsageApproval', [{"name":"","type":"address"},{"name":"","type":"address"}], [{"name":"","type":"uint256"}]),
]

print("=== xGRAIL Contract ===")
for fname, inputs, outputs in xgrail_funcs:
    try:
        abi = [{"constant": True, "inputs": inputs, "name": fname, "outputs": outputs, "type": "function"}]
        c = w3.eth.contract(address=xgrail_addr, abi=abi)
        fn = getattr(c.functions, fname)
        if len(inputs) == 0:
            val = fn().call()
        elif len(inputs) == 1:
            val = fn(wallet).call()
        elif len(inputs) == 2:
            # Try with dividends plugin
            val = fn(wallet, Web3.to_checksum_address('0xf7a5De5658ebc8e428901A35c53A6d398D06d69f')).call()
        if isinstance(val, int) and val > 1e10:
            print(f"  {fname}: {val/1e18:.6f} ({val})")
        else:
            print(f"  {fname}: {val}")
    except Exception as e:
        pass

# Check xGRAIL allocation to the harvest/dividends contract
print("\n=== xGRAIL Allocations ===")
harvest_addr = Web3.to_checksum_address('0xf7a5De5658ebc8e428901A35c53A6d398D06d69f')

for fname in ['usageAllocations', 'getUsageAllocation']:
    try:
        abi = [{"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": fname, "outputs": [{"name":"","type":"uint256"}], "type": "function"}]
        c = w3.eth.contract(address=xgrail_addr, abi=abi)
        val = getattr(c.functions, fname)(wallet, harvest_addr).call()
        print(f"  {fname} to harvest: {val/1e18:.6f}")
    except:
        pass

# Check if we can deallocate and redeem
print("\n=== Checking withdrawal functions ===")
# xGRAIL redeem flow: deallocate from plugin -> redeem xGRAIL to GRAIL (with vesting)
for fname in ['deallocate', 'deallocateFromUsage', 'withdraw', 'redeem']:
    # Check if function exists by trying estimateGas
    test_abis = [
        [{"inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": fname, "outputs": [], "stateMutability": "nonpayable", "type": "function"}],
        [{"inputs": [{"name":"","type":"uint256"},{"name":"","type":"uint256"}], "name": fname, "outputs": [], "stateMutability": "nonpayable", "type": "function"}],
        [{"inputs": [{"name":"","type":"uint256"}], "name": fname, "outputs": [], "stateMutability": "nonpayable", "type": "function"}],
    ]
    for test_abi in test_abis:
        try:
            c = w3.eth.contract(address=xgrail_addr, abi=test_abi)
            fn = getattr(c.functions, fname)
            input_count = len(test_abi[0]["inputs"])
            if input_count == 1:
                gas = fn(1).estimate_gas({"from": wallet})
            elif input_count == 2:
                gas = fn(harvest_addr, 1).estimate_gas({"from": wallet})
            print(f"  {fname}({input_count} args) exists! Gas: {gas}")
            break
        except Exception as e:
            err = str(e)
            if 'revert' in err.lower():
                print(f"  {fname}({input_count} args) exists but reverts: {err[:80]}")
                break

# ========== veAICODE ==========
print("\n=== veAICODE Lock Contract ===")
lock_addr = Web3.to_checksum_address('0x3a6D60bC404523F281Da5B5d6fD9beb2b348CBD7')

for fname in ['locked', 'lockedEnd', 'lockedAmount', 'balanceOf', 'unlockTime', 'lockEnd']:
    try:
        abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": fname, "outputs": [{"name":"","type":"uint256"}], "type": "function"}]
        c = w3.eth.contract(address=lock_addr, abi=abi)
        val = getattr(c.functions, fname)(wallet).call()
        if fname in ['lockedEnd', 'unlockTime', 'lockEnd'] and val > 1e9 and val < 2e10:
            import datetime
            dt = datetime.datetime.fromtimestamp(val)
            print(f"  {fname}: {val} ({dt.strftime('%Y-%m-%d %H:%M')})")
        elif isinstance(val, int) and val > 1e10:
            print(f"  {fname}: {val/1e18:.6f}")
        else:
            print(f"  {fname}: {val}")
    except:
        pass

# Try locked(address) which returns (amount, end) tuple
try:
    abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": "locked", "outputs": [{"name":"amount","type":"int128"},{"name":"end","type":"uint256"}], "type": "function"}]
    c = w3.eth.contract(address=lock_addr, abi=abi)
    amount, end = c.functions.locked(wallet).call()
    import datetime
    dt = datetime.datetime.fromtimestamp(end) if end > 0 else "no lock"
    print(f"  locked(): amount={amount/1e18:.6f}, end={dt}")
except Exception as e:
    print(f"  locked() tuple: {e}")

# Check withdraw
for fname in ['withdraw', 'unlock', 'emergencyWithdraw']:
    try:
        abi = [{"inputs": [], "name": fname, "outputs": [], "stateMutability": "nonpayable", "type": "function"}]
        c = w3.eth.contract(address=lock_addr, abi=abi)
        gas = c.functions.__getattr__(fname)().estimate_gas({"from": wallet})
        print(f"  {fname}() callable! Gas: {gas}")
    except Exception as e:
        err = str(e)
        if 'revert' in err.lower():
            print(f"  {fname}(): reverts - {err[:100]}")
