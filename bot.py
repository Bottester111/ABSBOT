
import os
import time
import logging
from web3 import Web3
from telegram import Bot

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RPC_URL = os.getenv("INFURA_URL")
FACTORY_ADDRESS = "0x59fC79d625380f803a1fc5028Fc3Dc7c8B3c3f1E"  # Proper checksum
POLL_INTERVAL = 3

# Debug output
print(f"🔑 TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN}")
print(f"📨 TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")
print(f"🔗 RPC_URL: {RPC_URL}")
print(f"🏭 FACTORY_ADDRESS: {FACTORY_ADDRESS}")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not RPC_URL:
    print("❌ Missing one or more required environment variables.")
    exit(1)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

factory = w3.eth.contract(address=FACTORY_ADDRESS, abi=[{
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
        {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
        {"indexed": False, "internalType": "address", "name": "pair", "type": "address"}
    ],
    "name": "PairCreated",
    "type": "event"
}])

seen_pairs = set()
last_block = w3.eth.block_number

def get_token_symbol(token_address):
    try:
        token = w3.eth.contract(address=token_address, abi=[{
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }])
        return token.functions.symbol().call()
    except Exception as e:
        logging.warning(f"Failed to get symbol for {token_address}: {e}")
        return "UNKNOWN"

def handle_new_pair(token0, token1, pair):
    sym0 = get_token_symbol(token0)
    sym1 = get_token_symbol(token1)
    message = f"🆕 New Pair Detected:\n\n{sym0} / {sym1}\nPair: {pair}"
    logging.info(f"Sending alert: {message}")
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")

def main():
    global last_block
    logging.info("Bot started.")
    while True:
        try:
            current_block = w3.eth.block_number
            events = factory.events.PairCreated().get_logs(fromBlock=last_block + 1, toBlock=current_block)
            logging.info(f"Scanning blocks {last_block + 1} to {current_block}... found {len(events)} events.")
            for event in events:
                pair = event["args"]["pair"]
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    handle_new_pair(event["args"]["token0"], event["args"]["token1"], pair)
            last_block = current_block
        except Exception as e:
            logging.error(f"Error during polling: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
