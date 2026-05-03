from pyrogram import Client, filters
from pyrogram.types import Message

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "🎯 <b>HubCloud Bypasser Bot</b>\n\n"
        "Send me any message containing one or more HubCloud links. Examples:\n"
        "<code>https://hubcloud.one/drive/abc123</code>\n"
        "<code>https://vifix.site/hubcloud/xyz789</code>\n"
        "or mixed with text: <code>KGF 2022 https://hubcloud.one/drive/abc123</code>\n\n"
        "✅ Multiple links in one message – each will be processed one by one.\n"
        "✅ You can also send links in separate messages – they will be queued.\n\n"
        "⚡ Powered by @MNBOTS logic",
        parse_mode="HTML"
    )
