"""
Swap ARB -> WETH via Uniswap V3 SwapRouter (original, simpler interface)
"""
import time
from web3 import Web3
from eth_account import Account

ARB_RPC = "https://arb1.arbitrum.io/rpc"
WALLET_ADDR = "0xe62aa01e03a55fB81D70c647b444178207A07aFe"

# Original Uniswap V3 SwapRouter on Arbitrum
V3_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

TOKENS = {
    "ARB":  "0x912CE59144191C1204E64559FE8253a0e49E6548",
    "WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
}

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "","type": "address"}], "name": "balanceOf", "outputs": [{"name": "","type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "","type": "address"},{"name": "","type": "uint256"}], "name": "approve", "outputs": [{"name": "","type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "","type": "address"},{"name": "","type": "address"}], "name": "allowance", "outputs": [{"name": "","type": "uint256"}], "type": "function"},
]

# V3 SwapRouter exactInputSingle - includes deadline
V3_ROUTER_ABI = [{
    "inputs": [{
        "components": [
            {"name": "tokenIn", "type": "address"},
            {"name": "tokenOut", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "recipient", "type": "address"},
            {"name": "deadline", "type": "uint256"},
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
}]


def load_wallet():
    Account.enable_unaudited_hdwallet_features()
    with open(r"C:\Users\kazhou\.openclaw\secrets\arb_wallet.key", "r") as f:
        return Account.from_mnemonic(f.read().strip())


def main():
    w3 = Web3(Web3.HTTPProvider(ARB_RPC))
    account = load_wallet()
    
    arb_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["ARB"]), abi=ERC20_ABI)
    arb_raw = arb_contract.functions.balanceOf(account.address).call()
    arb_balance = arb_raw / 1e18
    
    eth_bal = float(w3.from_wei(w3.eth.get_balance(account.address), 'ether'))
    print(f"Before: ARB={arb_balance:.2f} (~${arb_balance*0.10:.2f}), ETH={eth_bal:.6f}")
    
    if arb_balance < 1:
        print("Not enough ARB"); return
    
    # Approve for V3 Router
    allowance = arb_contract.functions.allowance(account.address, Web3.to_checksum_address(V3_ROUTER)).call()
    if allowance < arb_raw:
        print("Approving ARB for V3 Router...")
        nonce = w3.eth.get_transaction_count(account.address)
        tx = arb_contract.functions.approve(
            Web3.to_checksum_address(V3_ROUTER), arb_raw
        ).build_transaction({
            'from': account.address, 'nonce': nonce, 'gas': 100000,
            'maxFeePerGas': w3.eth.gas_price * 2,
            'maxPriorityFeePerGas': w3.to_wei(0.01, 'gwei'),
        })
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        print(f"  Approve: {'OK' if receipt.status == 1 else 'FAILED'} ({tx_hash.hex()[:16]}...)")
        time.sleep(2)
    else:
        print("Already approved for V3 Router")
    
    # Swap ARB -> WETH
    router = w3.eth.contract(address=Web3.to_checksum_address(V3_ROUTER), abi=V3_ROUTER_ABI)
    deadline = int(time.time()) + 300  # 5 minutes
    
    params = (
        Web3.to_checksum_address(TOKENS["ARB"]),   # tokenIn
        Web3.to_checksum_address(TOKENS["WETH"]),  # tokenOut
        500,                                         # fee (0.05%)
        account.address,                             # recipient
        deadline,                                    # deadline
        arb_raw,                                     # amountIn
        0,                                           # amountOutMinimum
        0,                                           # sqrtPriceLimitX96
    )
    
    nonce = w3.eth.get_transaction_count(account.address)
    tx = router.functions.exactInputSingle(params).build_transaction({
        'from': account.address, 'nonce': nonce, 'value': 0, 'gas': 300000,
        'maxFeePerGas': w3.eth.gas_price * 2,
        'maxPriorityFeePerGas': w3.to_wei(0.01, 'gwei'),
    })
    
    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Swap tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    print(f"Swap: {'OK' if receipt.status == 1 else 'FAILED'} | Gas: {receipt.gasUsed}")
    
    time.sleep(3)
    
    # After
    weth_contract = w3.eth.contract(address=Web3.to_checksum_address(TOKENS["WETH"]), abi=ERC20_ABI)
    weth_bal = weth_contract.functions.balanceOf(account.address).call() / 1e18
    arb_after = arb_contract.functions.balanceOf(account.address).call() / 1e18
    eth_after = float(w3.from_wei(w3.eth.get_balance(account.address), 'ether'))
    
    print(f"\nAfter:")
    print(f"  ARB:  {arb_after:.4f}")
    print(f"  WETH: {weth_bal:.6f} (~${weth_bal*2140:.2f})")
    print(f"  ETH:  {eth_after:.6f} (~${eth_after*2140:.2f})")


if __name__ == "__main__":
    main()
