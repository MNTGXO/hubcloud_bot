import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from utils.extractor import extract_hubcloud_urls, extract_direct_links, format_links_message

logger = logging.getLogger(__name__)

# Store per-user queues and worker tasks
user_queues: dict[int, asyncio.Queue] = {}
user_tasks: dict[int, asyncio.Task] = {}

# How long (seconds) a worker waits for a new URL before shutting itself down
WORKER_IDLE_TIMEOUT = 300  # 5 minutes


async def process_url(client: Client, user_id: int, url: str):
    """Process a single URL: extract links and send results to the user."""
    status_msg = await client.send_message(
        user_id,
        f"⏳ <b>Processing:</b>\n<code>{url}</code>\nPlease wait...",
        parse_mode="HTML"
    )
    try:
        links = await extract_direct_links(url)
        answer = format_links_message(links, url)

        # Create inline keyboard with download buttons (max 5)
        keyboard = [
            [InlineKeyboardButton(f"⬇️ {link['type']}", url=link['url'])]
            for link in links[:5]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await status_msg.edit_text(
            answer,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.exception("Failed to process %s", url)
        error_text = (
            f"❌ <b>Failed for:</b>\n<code>{url}</code>\n\n"
            f"<b>Reason:</b> <code>{e}</code>"
        )
        await status_msg.edit_text(error_text, parse_mode="HTML")


async def worker(client: Client, user_id: int, queue: asyncio.Queue):
    """
    Worker that pulls URLs from the user's queue and processes them one by one.

    FIX 1: Uses asyncio.wait_for with WORKER_IDLE_TIMEOUT so the task exits
            when the queue has been empty for 5 minutes, instead of blocking
            forever on queue.get(). This prevents the user_tasks / user_queues
            dicts from growing without bound (memory leak).

    FIX 2: Cleans up its own entries from user_tasks / user_queues on exit so
            the next message from the same user correctly spawns a fresh worker.
    """
    logger.info("Worker started for user %s", user_id)
    try:
        while True:
            try:
                url = await asyncio.wait_for(queue.get(), timeout=WORKER_IDLE_TIMEOUT)
            except asyncio.TimeoutError:
                # Queue has been idle long enough – stop the worker
                logger.info("Worker idle timeout for user %s, stopping", user_id)
                break

            try:
                await process_url(client, user_id, url)
            except Exception as e:
                logger.error("Worker error for user %s, url %s: %s", user_id, url, e)
            finally:
                queue.task_done()
                # Small delay between requests to avoid hitting rate limits
                await asyncio.sleep(1)
    finally:
        # FIX 2: Always clean up, even if the worker dies from an unexpected exception
        user_tasks.pop(user_id, None)
        user_queues.pop(user_id, None)
        logger.info("Worker cleaned up for user %s", user_id)


@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def handle_message(client: Client, message: Message):
    if not message.from_user:
        return

    user_id = message.from_user.id
    text = message.text or ""

    # Extract all HubCloud/Vifix URLs
    urls = extract_hubcloud_urls(text)
    if not urls:
        return

    # FIX 3: Re-create the queue if the old worker already cleaned it up
    if user_id not in user_queues:
        user_queues[user_id] = asyncio.Queue()

    # Add all URLs to the queue
    for url in urls:
        await user_queues[user_id].put(url)

    # Start a worker only if one isn't already running for this user
    existing_task = user_tasks.get(user_id)
    if existing_task is None or existing_task.done():
        task = asyncio.create_task(worker(client, user_id, user_queues[user_id]))
        user_tasks[user_id] = task

    # Acknowledge the queued links
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
