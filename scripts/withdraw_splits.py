"""Withdraw from 0xSplits on Arbitrum"""
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
weth_addr = Web3.to_checksum_address('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
bal_abi = [{"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"}]

# Check WETH before
weth_before = w3.eth.contract(address=weth_addr, abi=bal_abi).functions.balanceOf(wallet).call() / 1e18
print(f"WETH before: {weth_before:.6f}")

# 0xSplits - need to find the actual split contract
# From DeBank: 0.0474 WETH deposited in 0xSplits
# 0xSplits v2 uses a warehouse contract on Arbitrum
# Common 0xSplits warehouse address on Arbitrum
splits_warehouse = "0x8fb66F38cF86A3d5e8768f8F1754A24A6c661Fb8"

# Try the withdraw function
for fname in ['withdraw', 'withdrawFor']:
    try:
        # withdraw(address token) - withdraw all balance of a token
        abi = [{"inputs": [{"name":"","type":"address"}], "name": fname, "outputs": [], "stateMutability": "nonpayable", "type": "function"}]
        c = w3.eth.contract(address=Web3.to_checksum_address(splits_warehouse), abi=abi)
        gas = getattr(c.functions, fname)(weth_addr).estimate_gas({"from": wallet})
        print(f"{fname}(WETH) callable! Gas: {gas}")
    except Exception as e:
        err = str(e)[:120]
        print(f"{fname}: {err}")

# Try withdraw(address owner, address token)
try:
    abi = [{"inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"}]
    c = w3.eth.contract(address=Web3.to_checksum_address(splits_warehouse), abi=abi)
    gas = c.functions.withdraw(wallet, weth_addr).estimate_gas({"from": wallet})
    print(f"withdraw(wallet, WETH) callable! Gas: {gas}")
except Exception as e:
    err = str(e)[:120]
    print(f"withdraw(2 args): {err}")

# Check balance on warehouse
try:
    abi = [{"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"}]
    c = w3.eth.contract(address=Web3.to_checksum_address(splits_warehouse), abi=abi)
    bal = c.functions.balanceOf(wallet, weth_addr).call()
    print(f"Warehouse WETH balance: {bal/1e18:.6f}")
except Exception as e:
    print(f"balanceOf check: {str(e)[:80]}")
