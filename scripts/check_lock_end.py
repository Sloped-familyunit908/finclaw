from web3 import Web3
import datetime

w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
wallet = Web3.to_checksum_address('0xe62aa01e03a55fb81d70c647b444178207a07afe')
lock_addr = Web3.to_checksum_address('0x3a6D60bC404523F281Da5B5d6fD9beb2b348CBD7')

# Try to find lock end time
for fname in ['lockEnd', 'lockedEnd', 'userLockEnd', 'lockEndTime', 'endTime', 'unlockTime', 'end']:
    try:
        abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": fname, "outputs": [{"name":"","type":"uint256"}], "type": "function"}]
        c = w3.eth.contract(address=lock_addr, abi=abi)
        val = getattr(c.functions, fname)(wallet).call()
        if val > 1e9 and val < 2e10:
            dt = datetime.datetime.utcfromtimestamp(val)
            now = datetime.datetime.utcnow()
            days_left = (dt - now).days
            print(f"{fname}: {dt.strftime('%Y-%m-%d %H:%M UTC')} ({days_left} days left)")
        elif val > 0:
            print(f"{fname}: {val}")
    except:
        pass

# Check the IncreaseUnlockTime transaction to decode lock duration
tx = w3.eth.get_transaction('0x7972e2e4d48866e6293ea2105c3ce8f3c133f79f46c4418bddc52e54543ace52')
input_hex = tx.input.hex() if isinstance(tx.input, bytes) else tx.input
print(f"\nIncreaseUnlockTime tx input: {input_hex[:10]}")

if len(input_hex) >= 74:
    param = int(input_hex[10:74], 16)
    if param > 1e9 and param < 2e10:
        dt = datetime.datetime.utcfromtimestamp(param)
        now = datetime.datetime.utcnow()
        days_left = (dt - now).days
        print(f"Lock end time: {dt.strftime('%Y-%m-%d %H:%M UTC')} ({days_left} days)")
    else:
        print(f"Param (maybe duration seconds): {param} = {param/86400:.1f} days")

# Also try to read locked mapping with uint256 tokenId
try:
    abi = [{"constant": True, "inputs": [{"name":"","type":"uint256"}], "name": "locked", "outputs": [{"name":"","type":"int128"},{"name":"","type":"uint256"}], "type": "function"}]
    c = w3.eth.contract(address=lock_addr, abi=abi)
    for tid in [1, 2, 3]:
        try:
            amount, end = c.functions.locked(tid).call()
            if amount > 0:
                dt = datetime.datetime.utcfromtimestamp(end)
                print(f"locked({tid}): amount={amount/1e18:.2f}, end={dt.strftime('%Y-%m-%d')}")
        except:
            pass
except:
    pass

# Try user-specific lock info
try:
    abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": "userLock", "outputs": [{"name":"amount","type":"uint256"},{"name":"end","type":"uint256"},{"name":"","type":"uint256"}], "type": "function"}]
    c = w3.eth.contract(address=lock_addr, abi=abi)
    result = c.functions.userLock(wallet).call()
    print(f"userLock: {result}")
except:
    pass

# Simply read storage slot for the user's lock info
print("\nChecking last IncreaseUnlockTime calls to determine max lock end:")
# Your last IncreaseUnlockTime was 499 days ago with param
tx2 = w3.eth.get_transaction('0xb883ee523dfd9a01cdae891dbc720b5d4bd8386f7e74f55443e75b6cd79b23c8')
input2 = tx2.input.hex() if isinstance(tx2.input, bytes) else tx2.input
if len(input2) >= 74:
    param2 = int(input2[10:74], 16)
    if param2 > 1e9 and param2 < 2e10:
        dt2 = datetime.datetime.utcfromtimestamp(param2)
        now = datetime.datetime.utcnow()
        days_left = (dt2 - now).days
        print(f"Lock end: {dt2.strftime('%Y-%m-%d')} ({days_left} days left)")
    else:
        print(f"Param: {param2}")
