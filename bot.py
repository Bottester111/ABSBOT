
from web3 import Web3
import os
import time
from telegram import Bot
from web3.middleware import geth_poa_middleware

# Env variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RPC_URL = os.getenv("INFURA_URL")
FACTORY_RAW = "0x0D6848e39114abE69054407452b8aaB82f8a44BA"
POLL_INTERVAL = 3

bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Send startup confirmation
bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Moonshot bot is active and watching for new tokens.")

FACTORY_ADDRESS = Web3.to_checksum_address(FACTORY_RAW)
LAST_BLOCK = w3.eth.block_number

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
                            try:
                                token_contract = w3.eth.contract(address=token_addr, abi=[{"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":False,"stateMutability":"view","type":"function"}])
                                token_symbol = token_contract.functions.symbol().call()
                            except:
                                token_symbol = "???"
                            print(f"🚀 New Moonshot token: {token_addr} from TX {tx['hash'].hex()}")
                            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🚀 New token found!\n• Ticker: {token_symbol}\n• CA: {token_addr}\n• 🔗 DS: https://dexscreener.com/abstract/{token_addr}\n\n✅ Buy on Looter → @looter_ai_bot {token_addr}")
        LAST_BLOCK = latest
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    monitor_new_moonshot_tokens()
