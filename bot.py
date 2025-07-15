
import os
import time
from web3 import Web3
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from web3.middleware import geth_poa_middleware
from eth_abi import decode_single

# Env variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RPC_URL = os.getenv("INFURA_URL")
FACTORY_RAW = "0x0D6848e39114abE69054407452b8aaB82f8a44BA"
POLL_INTERVAL = 3

bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Moonshot bot is active and watching for new tokens.")

FACTORY_ADDRESS = Web3.to_checksum_address(FACTORY_RAW)
LAST_BLOCK = w3.eth.block_number

def get_token_symbol(token_addr):
    symbol_abi = [{
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }]
    try:
        contract = w3.eth.contract(address=token_addr, abi=symbol_abi)
        return contract.functions.symbol().call()
    except:
        try:
            raw = w3.eth.call({
                "to": token_addr,
                "data": "0x95d89b41"  # symbol()
            })
            try:
                return decode_single("string", raw)
            except:
                return decode_single("bytes32", raw).decode("utf-8").rstrip("\x00")
        except:
            return "???"

def monitor_new_moonshot_tokens():
    global LAST_BLOCK
    print("👀 Watching for NewMoonshotTokenAndBuy events...")
    while True:
        latest = w3.eth.block_number
        for block in range(LAST_BLOCK + 1, latest + 1):
            block_data = w3.eth.get_block(block, full_transactions=True)
            for tx in block_data['transactions']:
                if tx['to'] and tx['to'].lower() == FACTORY_ADDRESS.lower():
                    receipt = w3.eth.get_transaction_receipt(tx['hash'])
                    for log in receipt['logs']:
                        if log['address'].lower() == FACTORY_ADDRESS.lower() and log['topics'][0].hex() == "0x9b7f29228c2bdf9201f5a9ef2e3f3e976a30d9bd1720f7d0d63b472dcc675310":
                            token_addr = '0x' + log['data'].hex()[26:66]
                            token_symbol = get_token_symbol(token_addr)

                            print(f"🚀 New Moonshot token: {token_addr} | Symbol: {token_symbol}")

                            url = f"https://t.me/looter_ai_bot?start={token_addr}"
                            keyboard = [[InlineKeyboardButton("✅ Buy on Looter", url=url)]]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            bot.send_message(
                                chat_id=TELEGRAM_CHAT_ID,
                                text=f"🚀 New token found!\n• Ticker: {token_symbol}\n• CA: {token_addr}\n• 🔗 DS: https://dexscreener.com/abstract/{token_addr}",
                                reply_markup=reply_markup
                            )
        LAST_BLOCK = latest
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    monitor_new_moonshot_tokens()
