import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pyrogram import Client

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")

# Logging
logging.basicConfig(level=logging.INFO)
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

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not API_ID or not API_HASH:
        print("❌ ERROR: Please set BOT_TOKEN, API_ID, API_HASH environment variables.")
        print("   Get them from https://my.telegram.org/apps")
        exit(1)
    print("🚀 Bot is starting...")
    start_health_server()
    app.run()
