import os
import time
import requests
from web3 import Web3
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # 7760449431:AAGUBhQByU1qH3GGZqJO3A0G9A9tQMBrr64'
TELEGRAM_CHAT_IDS = ['-1002641458611', '-1002611461038']
INFURA_URL = os.environ.get('INFURA_URL')  # https://api.mainnet.abs.xyz'
MOONSHOT_CONTRACT_ADDRESS = os.environ.get('MOONSHOT_CONTRACT_ADDRESS')  # 0x0D6848e39114abE69054407452b8aaB82f8a44BA'
DEXSCREENER_API = 'https://api.dexscreener.com/latest/dex/tokens/'

ERC20_ABI = [
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
]

web3 = Web3(Web3.HTTPProvider(INFURA_URL))
bot = Bot(token=TELEGRAM_BOT_TOKEN)
seen_token_addresses = set()
waiting_queue = {}
MAX_RETRIES = 60
RETRY_INTERVAL = 2
LAUNCH_CUTOFF_SECONDS = 60
start_time = time.time() * 1000


def format_number(value):
    try:
        value = float(value)
        if value >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value/1_000:.2f}k"
        else:
            return f"{value:.6f}"
    except:
        return "Waiting..."

def get_dexscreener_data(token_address):
    try:
        res = requests.get(DEXSCREENER_API + token_address)
        if res.status_code == 200:
            data = res.json()
            pair = data.get('pairs', [{}])[0]
            if pair.get('priceUsd'):
                return {
                    'price': pair.get('priceUsd'),
                    'fdv': pair.get('fdv'),
                    'liquidity': pair.get('liquidity', {}).get('usd'),
                    'age': pair.get('pairCreatedAt'),
                    'volume': pair.get('volume', {}).get('h24'),
                    'symbol': pair.get('baseToken', {}).get('symbol'),
                    'link': f"https://dexscreener.com/abstract/{token_address}",
                    'image_url': pair.get('thumbnail'),
                    'buy_tax': pair.get('txns', {}).get('buyTax', 0),
                    'sell_tax': pair.get('txns', {}).get('sellTax', 0)
                }
    except:
        pass
    return {}

def format_age(timestamp_ms):
    try:
        age_sec = (time.time() * 1000 - int(timestamp_ms)) / 1000
        hours = int(age_sec // 3600)
        minutes = int((age_sec % 3600) // 60)
        return f"{hours}h{minutes:02d}m"
    except:
        return "Waiting..."

def send_alert_message(token_address, data):
    symbol = data.get('symbol', 'Unknown')
    link = data.get('link', 'N/A')
    price = format_number(data.get('price'))
    fdv = format_number(data.get('fdv'))
    liquidity = format_number(data.get('liquidity'))
    age = format_age(data.get('age'))
    volume = format_number(data.get('volume'))
    buy_tax = float(data.get('buy_tax', 0))
    sell_tax = float(data.get('sell_tax', 0))

    warnings = []
    if buy_tax > 10:
        warnings.append(f"⚠️ Buy Tax is {buy_tax:.2f}%")
    if sell_tax > 10:
        warnings.append(f"⚠️ Sell Tax is {sell_tax:.2f}%")

    message = (
        f"🚀 New token found!\n"
        f"• Ticker: {symbol}\n"
        f"• CA: {token_address}\n"
        f"• 🔗 DS: {link}\n"
        f"• 💸 Price: ${price}\n"
        f"• 💰 FDV: ${fdv}\n"
        f"• 💵 Liquidity: ${liquidity}\n"
        f"• ⏳ Pair Age: {age}\n"
        f"• 📊 Volume (24h): ${volume}"
    )
    if warnings:
        message += f"\n\n" + "\n".join(warnings)

    button = InlineKeyboardButton(
        text="✅ Buy on Looter",
        url=f"https://t.me/looter_ai_bot?start={token_address}"
    )
    markup = InlineKeyboardMarkup([[button]])

    for chat_id in TELEGRAM_CHAT_IDS:
        bot.send_message(chat_id=chat_id, text=message, reply_markup=markup)
        if 'image_url' in data and data['image_url']:
            try:
                bot.send_photo(chat_id=chat_id, photo=data['image_url'])
            except:
                pass

def check_moonshot_activity():
    latest_block = web3.eth.block_number
    block = web3.eth.get_block(latest_block, full_transactions=True)

    for tx in block.transactions:
        if tx.to and tx.to.lower() == MOONSHOT_CONTRACT_ADDRESS.lower():
            receipt = web3.eth.get_transaction_receipt(tx.hash)
            for log in receipt.logs:
                token_address = log.address
                if token_address.lower() in seen_token_addresses:
                    continue
                seen_token_addresses.add(token_address.lower())
                waiting_queue[token_address.lower()] = {
                    'retries': 0,
                    'timestamp': time.time()
                }

def process_waiting_queue():
    to_remove = []
    for token_address, meta in waiting_queue.items():
        if meta['retries'] >= MAX_RETRIES:
            to_remove.append(token_address)
            continue

        data = get_dexscreener_data(token_address)
        if data.get('price') and data.get('age') and int(data['age']) > start_time:
            send_alert_message(token_address, data)
            to_remove.append(token_address)
        else:
            waiting_queue[token_address]['retries'] += 1

    for token in to_remove:
        waiting_queue.pop(token, None)

def main():
    for chat_id in TELEGRAM_CHAT_IDS:
        bot.send_message(chat_id=chat_id, text="✅ Bot connected and monitoring Moonshot launches with token data...")
    while True:
        try:
            check_moonshot_activity()
            process_waiting_queue()
            time.sleep(RETRY_INTERVAL)
        except Exception as e:
            print("Error:", e)
            time.sleep(3)

if __name__ == '__main__':
    main()
