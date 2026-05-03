import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from utils.extractor import extract_hubcloud_urls, extract_direct_links, format_links_message

logger = logging.getLogger(__name__)

# Store per-user queues and worker tasks
user_queues = {}      # user_id -> asyncio.Queue
user_tasks = {}       # user_id -> asyncio.Task (worker)

async def process_url(client: Client, user_id: int, url: str, original_msg: Message):
    """
    Process a single URL: extract links and send results to the user.
    """
    status_msg = await client.send_message(
        user_id,
        f"⏳ <b>Processing:</b>\n<code>{url}</code>\nPlease wait...",
        parse_mode="HTML"
    )
    try:
        links = await extract_direct_links(url)
        answer = format_links_message(links, url)

        # Create inline keyboard with download buttons (max 5)
        keyboard = []
        for link in links[:5]:
            keyboard.append([InlineKeyboardButton(f"⬇️ {link['type']}", url=link['url'])])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await status_msg.edit_text(answer, parse_mode="HTML", reply_markup=reply_markup,
                                   disable_web_page_preview=False)
    except Exception as e:
        logger.exception(f"Failed to process {url}")
        error_text = f"❌ <b>Failed for:</b>\n<code>{url}</code>\n\n<b>Reason:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_text, parse_mode="HTML")

async def worker(client: Client, user_id: int, queue: asyncio.Queue):
    """
    Worker that pulls URLs from the user's queue and processes them one by one.
    """
    while True:
        url = await queue.get()
        try:
            await process_url(client, user_id, url, None)  # we don't need the original message object here
        except Exception as e:
            logger.error(f"Worker error for user {user_id}, url {url}: {e}")
        finally:
            queue.task_done()
            # Small delay between requests to avoid hitting rate limits
            await asyncio.sleep(1)

@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def handle_message(client: Client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    text = message.text

    # Extract all HubCloud/Vifix URLs
    urls = extract_hubcloud_urls(text)
    if not urls:
        # Ignore messages without any target URL
        return

    # Initialize queue for this user if not exists
    if user_id not in user_queues:
        user_queues[user_id] = asyncio.Queue()

    # Add all URLs to the queue
    for url in urls:
        await user_queues[user_id].put(url)

    # Start a worker for the user if not already running
    if user_id not in user_tasks or user_tasks[user_id].done():
        task = asyncio.create_task(worker(client, user_id, user_queues[user_id]))
        user_tasks[user_id] = task

    # Let the user know how many links were added
    if len(urls) == 1:
        await message.reply_text(
            f"✅ <b>Added to queue:</b>\n<code>{urls[0]}</code>\nI'll process it shortly.",
            parse_mode="HTML"
        )
    else:
        await message.reply_text(
            f"✅ <b>Added {len(urls)} links to queue.</b>\nThey will be processed one by one.",
            parse_mode="HTML"
        )
