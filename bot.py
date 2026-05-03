import os
import sys
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client
from pyrogram.types import BotCommand
from pyrogram import idle

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
API_ID_RAW = os.environ.get("API_ID", "0").strip()
API_HASH = os.environ.get("API_HASH", "")

try:
    API_ID = int(API_ID_RAW)
except ValueError:
    API_ID = 0

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health check server listening on port %s", port)

# Create Pyrogram client
app = Client(
    "hubcloud_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")   # Auto-load plugins from the "plugins" folder
)

ADMIN_NOTIFY_ID = 1892771262

if __name__ == "__main__":
    logger.info("Booting hubcloud bot process")
    logger.info("Env check: BOT_TOKEN=%s API_ID=%s API_HASH=%s PORT=%s",
                "set" if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else "missing",
                API_ID_RAW or "missing",
                "set" if API_HASH else "missing",
                os.environ.get("PORT", "8080"))

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not API_ID or not API_HASH:
        print("❌ ERROR: Please set BOT_TOKEN, API_ID, API_HASH environment variables.")
        print("   Get them from https://my.telegram.org/apps")
        exit(1)

    print("🚀 Bot is starting...")
    start_health_server()
    try:
        app.start()
        logger.info("Pyrogram client started")

        # NOTE: Pyrogram uses MTProto, not the Bot API — no webhook management needed.
        # delete_webhook() is a Bot API concept (python-telegram-bot / aiogram) and
        # does not exist in Pyrogram. Long polling is the default behaviour here.

        app.set_bot_commands([
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show usage help"),
        ])
        logger.info("Bot commands registered")

        try:
            app.send_message(
                ADMIN_NOTIFY_ID,
                "✅ HubCloud bot restarted successfully and is now online."
            )
            logger.info("Startup notification sent to %s", ADMIN_NOTIFY_ID)
        except Exception:
            logger.exception("Failed to send startup notification to %s", ADMIN_NOTIFY_ID)

        idle()
    except Exception:
        logger.exception("Fatal error while running bot")
        sys.exit(1)
    finally:
        try:
            app.stop()
        except Exception:
            logger.exception("Error during bot shutdown")
