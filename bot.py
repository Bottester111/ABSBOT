
import os
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print(f"Using token: {TELEGRAM_BOT_TOKEN}")
print(f"Chat ID: {TELEGRAM_CHAT_ID}")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
    exit(1)

try:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Telegram bot test successful!")
    print("✅ Message sent successfully.")
except Exception as e:
    print(f"❌ Error sending message: {e}")
