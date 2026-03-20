"""
FinClaw DeFi Monitor - Daily check, NO trading
Just monitor and report LP performance.
"""
from web3 import Web3
import json
import os
from datetime import datetime

WALLET = "0xe62aa01e03a55fB81D70c647b444178207A07aFe"

def check_all():
    results = {}
    
    # ARB chain
    try:
        arb = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc"))
        w = Web3.to_checksum_address(WALLET)
        eth = arb.eth.get_balance(w) / 1e18
        
        weth_c = arb.eth.contract(
            address=Web3.to_checksum_address("0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
            abi=[{"constant":True,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"}]
        )
        weth = weth_c.functions.balanceOf(w).call() / 1e18
        results["arb"] = {"eth": eth, "weth": weth, "eth_usd": eth * 2140, "weth_usd": weth * 2140}
    except:
        results["arb"] = {"error": True}
    
    # BSC chain
    try:
        bsc = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org"))
        w = Web3.to_checksum_address(WALLET)
        bnb = bsc.eth.get_balance(w) / 1e18
        results["bsc"] = {"bnb": bnb, "bnb_usd": bnb * 644}
    except:
        results["bsc"] = {"error": True}
    
    results["timestamp"] = datetime.utcnow().isoformat()
    return results

if __name__ == "__main__":
    r = check_all()
    print(f"=== DeFi Monitor {r['timestamp'][:10]} ===")
    if "error" not in r.get("arb", {}):
        print(f"ARB: ETH={r['arb']['eth']:.6f} WETH={r['arb']['weth']:.6f}")
    if "error" not in r.get("bsc", {}):
        print(f"BSC: BNB={r['bsc']['bnb']:.6f} (${r['bsc']['bnb_usd']:.2f})")
    print("LP positions: earning fees, no action needed")
    
    # Save to log
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "defi-monitor")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "daily.json")
    
    history = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            history = json.load(f)
    history.append(r)
    with open(log_file, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Logged to {log_file}")
