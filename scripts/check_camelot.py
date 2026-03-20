from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))
wallet = Web3.to_checksum_address('0xe62aa01e03a55fb81d70c647b444178207a07afe')
harvest = Web3.to_checksum_address('0xf7a5De5658ebc8e428901A35c53A6d398D06d69f')

# This is a Camelot Nitro Pool or Dividends Plugin
# Let's check total supply and total staked to understand scale
for fname, inputs, outputs in [
    ('totalSupply', [], [{'name':'','type':'uint256'}]),
    ('totalStaked', [], [{'name':'','type':'uint256'}]),
    ('totalAllocation', [], [{'name':'','type':'uint256'}]),
    ('rewardPerToken', [], [{'name':'','type':'uint256'}]),
    ('lastRewardTime', [], [{'name':'','type':'uint256'}]),
    ('rewardRate', [], [{'name':'','type':'uint256'}]),
    ('totalRewardsDistributed', [], [{'name':'','type':'uint256'}]),
    ('owner', [], [{'name':'','type':'address'}]),
]:
    try:
        abi = [{'constant': True, 'inputs': inputs, 'name': fname, 'outputs': outputs, 'type': 'function'}]
        c = w3.eth.contract(address=harvest, abi=abi)
        val = getattr(c.functions, fname)().call()
        if isinstance(val, int) and val > 1e15:
            print(f"{fname}: {val/1e18:.6f} (raw: {val})")
        else:
            print(f"{fname}: {val}")
    except:
        pass

# Try to harvest just to see if it would succeed - estimate gas
from eth_account import Account
Account.enable_unaudited_hdwallet_features()
with open(r"C:\Users\kazhou\.openclaw\secrets\arb_wallet.key") as f:
    acct = Account.from_mnemonic(f.read().strip())

# Try calling harvest with estimateGas to see if it would work
for fname in ['harvest', 'claim', 'getReward', 'harvestAll']:
    try:
        abi = [{'constant': False, 'inputs': [], 'name': fname, 'outputs': [], 'type': 'function'}]
        c = w3.eth.contract(address=harvest, abi=abi)
        gas = c.functions.__getattr__(fname)().estimate_gas({'from': acct.address})
        print(f"\n{fname}() would cost ~{gas} gas - CALLABLE!")
    except Exception as e:
        err = str(e)
        if 'execution reverted' in err.lower():
            print(f"{fname}(): would revert - {err[:100]}")
        elif 'no data' in err.lower() or 'could not' in err.lower():
            pass  # function doesn't exist
        else:
            print(f"{fname}(): {err[:100]}")
