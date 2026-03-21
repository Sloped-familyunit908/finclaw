from web3 import Web3
from eth_account import Account
import time

Account.enable_unaudited_hdwallet_features()
w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))

import os
_SECRETS_DIR = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))

with open(os.path.join(_SECRETS_DIR, "arb_wallet.key")) as f:
    acct = Account.from_mnemonic(f.read().strip())

grail_addr = Web3.to_checksum_address('0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8')
xgrail_addr = Web3.to_checksum_address('0x3CAaE25Ee616f2C8E13C74dA0813402eae3F496b')
bal_abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"}]

grail_before = w3.eth.contract(address=grail_addr, abi=bal_abi).functions.balanceOf(acct.address).call() / 1e18
xgrail_before = w3.eth.contract(address=xgrail_addr, abi=bal_abi).functions.balanceOf(acct.address).call() / 1e18
print(f"Before: GRAIL={grail_before:.6f}, xGRAIL={xgrail_before:.6f}")

# Harvest
harvest_addr = Web3.to_checksum_address('0xf7a5De5658ebc8e428901A35c53A6d398D06d69f')
abi = [{"inputs": [], "name": "harvest", "outputs": [], "stateMutability": "nonpayable", "type": "function"}]
c = w3.eth.contract(address=harvest_addr, abi=abi)

nonce = w3.eth.get_transaction_count(acct.address)
tx = c.functions.harvest().build_transaction({
    "from": acct.address, "nonce": nonce, "gas": 200000,
    "maxFeePerGas": w3.eth.gas_price * 2,
    "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"),
})
signed = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f"Harvest tx: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
status = "OK" if receipt.status == 1 else "FAILED"
print(f"Status: {status} | Gas: {receipt.gasUsed}")

time.sleep(2)

grail_after = w3.eth.contract(address=grail_addr, abi=bal_abi).functions.balanceOf(acct.address).call() / 1e18
xgrail_after = w3.eth.contract(address=xgrail_addr, abi=bal_abi).functions.balanceOf(acct.address).call() / 1e18
grail_earned = grail_after - grail_before
xgrail_earned = xgrail_after - xgrail_before
print(f"After:  GRAIL={grail_after:.6f}, xGRAIL={xgrail_after:.6f}")
print(f"Earned: GRAIL={grail_earned:.6f} (~${grail_earned*82:.2f})")
print(f"Earned: xGRAIL={xgrail_earned:.6f} (~${xgrail_earned*82:.2f})")
