import os
import logging
from pyrogram import Client

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Pyrogram client
app = Client(
    "hubcloud_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")   # Auto-load plugins from the "plugins" folder
)

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not API_ID or not API_HASH:
        print("❌ ERROR: Please set BOT_TOKEN, API_ID, API_HASH environment variables.")
        print("   Get them from https://my.telegram.org/apps")
        exit(1)
    print("🚀 Bot is starting...")
    app.run()
