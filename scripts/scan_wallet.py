"""Scan all token balances in the ARB wallet"""
import json
import urllib.request
from web3 import Web3

WALLET = Web3.to_checksum_address("0xe62aa01e03a55fb81d70c647b444178207a07afe")
ARB_RPC = "https://arb1.arbitrum.io/rpc"

# Common tokens on Arbitrum with their contract addresses
KNOWN_TOKENS = {
    "USDC": {"addr": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6},
    "USDC.e": {"addr": "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8", "decimals": 6},
    "USDT": {"addr": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "decimals": 6},
    "WETH": {"addr": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "decimals": 18},
    "ARB": {"addr": "0x912CE59144191C1204E64559FE8253a0e49E6548", "decimals": 18},
    "DAI": {"addr": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1", "decimals": 18},
    "WBTC": {"addr": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f", "decimals": 8},
    "GMX": {"addr": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a", "decimals": 18},
    "LINK": {"addr": "0xf97f4df75117a78c1A5a0DBb814Af92458539FB4", "decimals": 18},
    "UNI": {"addr": "0xFa7F8980b0f1E64A2062791cc3b0871572f1F7f0", "decimals": 18},
    "MAGIC": {"addr": "0x539bdE0d7Dbd336b79148AA742883198BBF60342", "decimals": 18},
    "RDNT": {"addr": "0x3082CC23568eA640225c2467653dB90e9250AaA0", "decimals": 18},
    "PENDLE": {"addr": "0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8", "decimals": 18},
    "GNS": {"addr": "0x18c11FD286C5EC11c3b683Caa813B77f5163A122", "decimals": 18},
    "GRAIL": {"addr": "0x3d9907F9a368ad0a51Be60f7Da3b97cf940982D8", "decimals": 18},
    "JONES": {"addr": "0x10393c20975cF177a3513071bC110f7962CD67da", "decimals": 18},
    "DPX": {"addr": "0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55", "decimals": 18},
    "VSTA": {"addr": "0xa684cd057951541187f288294a1e1C2646aA2d24", "decimals": 18},
    "SPA": {"addr": "0x5575552988A3A80504bBaeB1311674fCFd40aA4B", "decimals": 18},
    "USDs": {"addr": "0xD74f5255D557944cf7Dd0E45FF521520002D5748", "decimals": 18},
}

ERC20_ABI = json.dumps([{
    "constant": True, "inputs": [{"name": "_owner", "type": "address"}],
    "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
    "type": "function"
}])

w3 = Web3(Web3.HTTPProvider(ARB_RPC))

print(f"Wallet: {WALLET}")
print(f"Connected: {w3.is_connected()}")
print()

# ETH balance
eth_bal = w3.from_wei(w3.eth.get_balance(WALLET), 'ether')
print(f"{'ETH':<12} {float(eth_bal):>15.6f}  (~${float(eth_bal)*2140:.2f})")

# Token balances
abi = json.loads(ERC20_ABI)
for name, info in KNOWN_TOKENS.items():
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(info["addr"]),
            abi=abi
        )
        raw = contract.functions.balanceOf(Web3.to_checksum_address(WALLET)).call()
        balance = raw / (10 ** info["decimals"])
        if balance > 0.0001:
            print(f"{name:<12} {balance:>15.6f}")
    except Exception as e:
        pass

print("\nDone scanning known tokens.")
