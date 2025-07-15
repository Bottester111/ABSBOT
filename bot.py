
import asyncio
import json
import os
import time
import aiohttp
from web3 import Web3
from eth_abi import decode as eth_decode

# Load environment variables
INFURA_URL = os.getenv("INFURA_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", 2))

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
contract_address = Web3.to_checksum_address(CONTRACT_ADDRESS)

# Load ABI
with open("abi.json") as f:
    abi = json.load(f)

contract = w3.eth.contract(address=contract_address, abi=abi)

# Track processed tx hashes
seen_tx_hashes = set()

async def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.text()

def parse_event_data(log):
    try:
        raw_data = log["data"]
        # Ensure valid hex format by removing double 0x
        if raw_data.startswith("0x0x"):
            raw_data = raw_data[2:]

        decoded = eth_decode(["uint256", "address", "uint256"], bytes.fromhex(raw_data[2:]))
        amount, token_address, price = decoded
        return amount, token_address, price
    except Exception as e:
        print(f"Error decoding log: {e}")
        return None

async def scan():
    print("👀 Watching for NewMoonshotTokenAndBuy events...")
    while True:
        try:
            latest = w3.eth.block_number
            events = contract.events.NewMoonshotTokenAndBuy().get_logs(fromBlock=latest - 3, toBlock=latest)

            for event in events:
                tx_hash = event["transactionHash"].hex()
                if tx_hash in seen_tx_hashes:
                    continue
                seen_tx_hashes.add(tx_hash)

                parsed = parse_event_data(event)
                if parsed:
                    amount, token_address, price = parsed
                    message = (
                        f"🚀 *New token found!*
"
                        f"💰 Buy Amount: {amount / 1e18:.4f} ETH
"
                        f"🔗 Token: [{token_address}](https://dexscreener.com/ethereum/{token_address})
"
                        f"💸 Price: {price / 1e18:.6f} ETH"
                    )
                    await send_telegram_message(message)

        except Exception as e:
            print(f"Error while scanning: {e}")

        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(scan())
