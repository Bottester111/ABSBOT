import os
import time
import json
import requests

def to_hex(value: bytes) -> str:
    hex_str = value.hex()
    return hex_str if hex_str.startswith("0x") else "0x" + hex_str

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

# Load environment variables
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet.abs.xyz")
FACTORY_ADDRESS = Web3.to_checksum_address(os.getenv("FACTORY_ADDRESS") or "0x0D6848e39114abE69054407452b8aaB82f8a44BA")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Event signature and topic hash for NewMoonshotTokenAndBuy
NEW_TOKEN_EVENT_SIG = "NewMoonshotTokenAndBuy(address,address,bytes,uint256,uint256,uint256,uint256,uint256)"
NEW_TOKEN_TOPIC = w3.keccak(text=NEW_TOKEN_EVENT_SIG).hex()

def send_telegram_message(text, inline_url=None, button_label=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    if inline_url and button_label:
        payload["reply_markup"] = json.dumps({
            "inline_keyboard": [[{"text": button_label, "url": inline_url}]]
        })
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def get_token_symbol(token_address):
    abi_symbol_string = {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }

    abi_symbol_bytes = {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "bytes32"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }

    contract = w3.eth.contract(address=token_address, abi=[abi_symbol_string])
    try:
        return contract.functions.symbol().call()
    except:
        try:
            contract = w3.eth.contract(address=token_address, abi=[abi_symbol_bytes])
            raw = contract.functions.symbol().call()
            return w3.to_text(raw).replace("\x00", "").strip()
        except:
            return "???"

def monitor_new_moonshot_tokens():
    send_telegram_message("✅ *Moonshot bot is active and watching for new tokens!*")
    print("👀 Watching for NewMoonshotTokenAndBuy events...")

    last_block = w3.eth.block_number
    while True:
        try:
            logs = w3.eth.get_logs({
                "fromBlock": last_block,
                "toBlock": "latest",
                "address": FACTORY_ADDRESS,
                "topics": [NEW_TOKEN_TOPIC]
            })

            for log in logs:
                token_addr = to_checksum_address("0x" + log["data"][26:66].hex())
                symbol = get_token_symbol(token_addr)

                msg = f"""🚀 *New token found!*
• Ticker: {symbol}
• CA: {token_addr}
• 🔗 DS: https://dexscreener.com/abstract/{token_addr}"""

                looter_url = f"https://t.me/looter_ai_bot?start={token_addr}"
                send_telegram_message(msg, inline_url=looter_url, button_label="✅ Buy on Looter")
                print(f"🚀 New Moonshot token: {token_addr}")

            last_block = w3.eth.block_number
        except Exception as e:
            print(f"Error while scanning: {e}")

        time.sleep(3)

if __name__ == "__main__":
    monitor_new_moonshot_tokens()