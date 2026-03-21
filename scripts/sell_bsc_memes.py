"""Scan and sell meme tokens on BNB Chain, then do LP"""
from web3 import Web3
from eth_account import Account
import time
import json
import urllib.request

Account.enable_unaudited_hdwallet_features()
bsc = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org'))
import os
_SECRETS_DIR = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))
with open(os.path.join(_SECRETS_DIR, "arb_wallet.key")) as f:
    acct = Account.from_mnemonic(f.read().strip())

wallet = acct.address
print(f"Wallet: {wallet}")
print(f"BNB: {bsc.eth.get_balance(wallet)/1e18:.6f} (${bsc.eth.get_balance(wallet)/1e18*644:.2f})")

# Known BSC tokens from DeBank
BSC_TOKENS = {
    "BabyDoge": "0xc748673057861a797275CD8A068AbB95A902e8de",
    "BabyShibaInu": "0x4e690b585af553582e11681D756d17B1aC2e644f",
    "MOONRABBIT": "0x431B1acFeedDb04eBa94f3e3d0bDd8E56E657a3c",
    "REDFEG": "0x5fa54fdDf15A0c32f1a5b0E2E8dD5A7E3DfB2457",
    "SURGE": "0xE1E1Aa58983F6b8eE8E4eCD206ceA6578F036768",
    "BTCB": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
    "USDT": "0x55d398326f99059fF775485246999027B3197955",
}

ERC20_ABI = [
    {"constant": True, "inputs": [{"name":"","type":"address"}], "name": "balanceOf", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name":"","type":"uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name":"","type":"address"},{"name":"","type":"uint256"}], "name": "approve", "outputs": [{"name":"","type":"bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name":"","type":"address"},{"name":"","type":"address"}], "name": "allowance", "outputs": [{"name":"","type":"uint256"}], "type": "function"},
]

# PancakeSwap V2 Router on BSC
PANCAKE_ROUTER = Web3.to_checksum_address("0x10ED43C718714eb63d5aA57B78B54704E256024E")
WBNB = Web3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")

PANCAKE_ABI = [{
    "inputs": [
        {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMin", "type": "uint256"},
        {"name": "path", "type": "address[]"},
        {"name": "to", "type": "address"},
        {"name": "deadline", "type": "uint256"}
    ],
    "name": "swapExactTokensForETHSupportingFeeOnTransferTokens",
    "outputs": [],
    "stateMutability": "nonpayable",
    "type": "function"
}, {
    "inputs": [
        {"name": "amountIn", "type": "uint256"},
        {"name": "path", "type": "address[]"},
    ],
    "name": "getAmountsOut",
    "outputs": [{"name": "amounts", "type": "uint256[]"}],
    "stateMutability": "view",
    "type": "function"
}]

# Check all token balances
print("\n=== BSC Token Balances ===")
tokens_to_sell = []
for name, addr in BSC_TOKENS.items():
    try:
        c = bsc.eth.contract(address=Web3.to_checksum_address(addr), abi=ERC20_ABI)
        bal = c.functions.balanceOf(wallet).call()
        dec = c.functions.decimals().call()
        human_bal = bal / (10**dec)
        if bal > 0:
            # Try to get quote
            try:
                router = bsc.eth.contract(address=PANCAKE_ROUTER, abi=PANCAKE_ABI)
                amounts = router.functions.getAmountsOut(bal, [Web3.to_checksum_address(addr), WBNB]).call()
                bnb_out = amounts[1] / 1e18
                usd_out = bnb_out * 644
                print(f"  {name}: {human_bal:.4f} -> {bnb_out:.6f} BNB (${usd_out:.2f})")
                if usd_out > 0.5:  # Only sell if worth more than $0.50
                    tokens_to_sell.append((name, addr, bal, dec, usd_out))
            except:
                print(f"  {name}: {human_bal:.4f} (no liquidity)")
    except:
        pass

print(f"\n=== Selling {len(tokens_to_sell)} tokens ===")
router = bsc.eth.contract(address=PANCAKE_ROUTER, abi=PANCAKE_ABI)

for name, addr, bal, dec, est_usd in tokens_to_sell:
    print(f"\nSelling {name} (~${est_usd:.2f})...")
    token_addr = Web3.to_checksum_address(addr)
    tc = bsc.eth.contract(address=token_addr, abi=ERC20_ABI)
    
    # Approve
    allowance = tc.functions.allowance(wallet, PANCAKE_ROUTER).call()
    if allowance < bal:
        nonce = bsc.eth.get_transaction_count(wallet)
        tx = tc.functions.approve(PANCAKE_ROUTER, bal).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 100000,
            "gasPrice": bsc.eth.gas_price,
        })
        signed = acct.sign_transaction(tx)
        h = bsc.eth.send_raw_transaction(signed.raw_transaction)
        r = bsc.eth.wait_for_transaction_receipt(h, timeout=60)
        status = "OK" if r.status == 1 else "FAILED"
        print(f"  Approve: {status}")
        time.sleep(2)
    
    # Sell via PancakeSwap (use supportingFeeOnTransferTokens for meme coins with transfer tax)
    try:
        nonce = bsc.eth.get_transaction_count(wallet)
        deadline = int(time.time()) + 300
        tx = router.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
            bal, 0, [token_addr, WBNB], wallet, deadline
        ).build_transaction({
            "from": wallet, "nonce": nonce, "gas": 300000,
            "gasPrice": bsc.eth.gas_price,
        })
        signed = acct.sign_transaction(tx)
        h = bsc.eth.send_raw_transaction(signed.raw_transaction)
        r = bsc.eth.wait_for_transaction_receipt(h, timeout=120)
        status = "OK" if r.status == 1 else "FAILED"
        print(f"  Swap: {status} | Gas: {r.gasUsed}")
    except Exception as e:
        print(f"  Swap failed: {str(e)[:100]}")
    
    time.sleep(1)

# Final BNB balance
bnb_after = bsc.eth.get_balance(wallet) / 1e18
print(f"\n=== Final BNB Balance ===")
print(f"BNB: {bnb_after:.6f} (${bnb_after*644:.2f})")
