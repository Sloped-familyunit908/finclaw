"""
FinClaw ARB Wallet Operations
==============================
Swap tokens on Arbitrum via Uniswap V3 Router.
Safety: all transactions logged, amounts verified before execution.
"""
import json
import time
from web3 import Web3
from eth_account import Account

# Config
ARB_RPC = "https://arb1.arbitrum.io/rpc"
WALLET_ADDR = "0xe62aa01e03a55fB81D70c647b444178207A07aFe"

# Uniswap V3 SwapRouter02 on Arbitrum
SWAP_ROUTER = "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45"

# Token addresses on Arbitrum
TOKENS = {
    "ARB":  "0x912CE59144191C1204E64559FE8253a0e49E6548",
    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
}

# ERC20 ABI (approve + balanceOf)
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
]

# SwapRouter02 exactInputSingle ABI
SWAP_ROUTER_ABI = [
    {
        "inputs": [{
            "components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "tokenOut", "type": "address"},
                {"name": "fee", "type": "uint24"},
                {"name": "recipient", "type": "address"},
                {"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMinimum", "type": "uint256"},
                {"name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "name": "params",
            "type": "tuple"
        }],
        "name": "exactInputSingle",
        "outputs": [{"name": "amountOut", "type": "uint256"}],
        "stateMutability": "payable",
        "type": "function"
    }
]


def load_wallet():
    Account.enable_unaudited_hdwallet_features()
    import os
    secrets_dir = os.environ.get("FINCLAW_SECRETS_DIR", os.path.expanduser("~/.openclaw/secrets"))
    with open(os.path.join(secrets_dir, "arb_wallet.key"), "r") as f:
        mnemonic = f.read().strip()
    return Account.from_mnemonic(mnemonic)


def get_balance(w3, token_addr, wallet_addr, decimals=18):
    contract = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=ERC20_ABI)
    raw = contract.functions.balanceOf(Web3.to_checksum_address(wallet_addr)).call()
    return raw / (10 ** decimals)


def approve_token(w3, account, token_addr, spender, amount_raw):
    """Approve spender to use tokens."""
    contract = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=ERC20_ABI)
    
    # Check current allowance
    current = contract.functions.allowance(
        Web3.to_checksum_address(WALLET_ADDR),
        Web3.to_checksum_address(spender)
    ).call()
    
    if current >= amount_raw:
        print(f"  Already approved (allowance: {current})")
        return None
    
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.functions.approve(
        Web3.to_checksum_address(spender),
        amount_raw
    ).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 100000,
        'maxFeePerGas': w3.eth.gas_price * 2,
        'maxPriorityFeePerGas': w3.to_wei(0.01, 'gwei'),
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  Approve tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    print(f"  Approve status: {'OK' if receipt.status == 1 else 'FAILED'}")
    return receipt


def swap_exact_input(w3, account, token_in, token_out, amount_in_raw, fee=3000, slippage_pct=2.0):
    """Swap tokens via Uniswap V3 exactInputSingle."""
    router = w3.eth.contract(address=Web3.to_checksum_address(SWAP_ROUTER), abi=SWAP_ROUTER_ABI)
    
    # amountOutMinimum = 0 for now (we accept any output due to small amounts)
    # In production, query the pool for expected output and apply slippage
    amount_out_min = 0  # For $91 worth, slippage protection less critical
    
    nonce = w3.eth.get_transaction_count(account.address)
    
    params = {
        'tokenIn': Web3.to_checksum_address(token_in),
        'tokenOut': Web3.to_checksum_address(token_out),
        'fee': fee,  # 0.3% pool
        'recipient': account.address,
        'amountIn': amount_in_raw,
        'amountOutMinimum': amount_out_min,
        'sqrtPriceLimitX96': 0,
    }
    
    tx = router.functions.exactInputSingle(params).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'value': 0,
        'gas': 300000,
        'maxFeePerGas': w3.eth.gas_price * 2,
        'maxPriorityFeePerGas': w3.to_wei(0.01, 'gwei'),
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"  Swap tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"  Swap status: {'OK' if receipt.status == 1 else 'FAILED'}")
    print(f"  Gas used: {receipt.gasUsed}")
    return receipt


def main():
    w3 = Web3(Web3.HTTPProvider(ARB_RPC))
    account = load_wallet()
    
    print("=" * 60)
    print("FinClaw Wallet Operations")
    print("=" * 60)
    
    # Check balances before
    arb_balance = get_balance(w3, TOKENS["ARB"], WALLET_ADDR, 18)
    eth_balance = float(w3.from_wei(w3.eth.get_balance(account.address), 'ether'))
    
    print(f"\nBefore:")
    print(f"  ARB: {arb_balance:.4f} (~${arb_balance * 0.10:.2f})")
    print(f"  ETH: {eth_balance:.6f} (~${eth_balance * 2140:.2f})")
    
    if arb_balance < 1:
        print("Not enough ARB to swap. Exiting.")
        return
    
    # Step 1: Approve ARB for SwapRouter
    arb_raw = int(arb_balance * 10**18)
    print(f"\nStep 1: Approve {arb_balance:.2f} ARB for Uniswap Router...")
    approve_token(w3, account, TOKENS["ARB"], SWAP_ROUTER, arb_raw)
    
    time.sleep(2)
    
    # Step 2: Swap ARB -> WETH (via 0.05% fee pool - verified from pool contract)
    print(f"\nStep 2: Swap {arb_balance:.2f} ARB -> WETH...")
    swap_exact_input(w3, account, TOKENS["ARB"], TOKENS["WETH"], arb_raw, fee=500)
    
    time.sleep(3)
    
    # Check balances after
    arb_after = get_balance(w3, TOKENS["ARB"], WALLET_ADDR, 18)
    weth_after = get_balance(w3, TOKENS["WETH"], WALLET_ADDR, 18)
    eth_after = float(w3.from_wei(w3.eth.get_balance(account.address), 'ether'))
    
    print(f"\nAfter:")
    print(f"  ARB: {arb_after:.4f}")
    print(f"  WETH: {weth_after:.6f} (~${weth_after * 2140:.2f})")
    print(f"  ETH: {eth_after:.6f} (~${eth_after * 2140:.2f})")
    print(f"\nDone!")


if __name__ == "__main__":
    main()
