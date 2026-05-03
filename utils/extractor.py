import re
import logging
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# CORS proxies (same as HTML version)
CORS_PROXIES = [
    "https://api.allorigins.win/get?url=",
    "https://thingproxy.freeboard.io/fetch/",
    "https://cors-anywhere.herokuapp.com/",
    "https://proxy.cors.sh/",
    "https://api.codetabs.com/v1/proxy?quest="
]
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def normalize_url(url: str) -> str:
    """Convert vifix.site/hubcloud/xxx → hubcloud.one/drive/xxx"""
    url = url.strip()
    vifix_pattern = r"^https?://vifix\.site/hubcloud/([a-z0-9]+)$"
    match = re.search(vifix_pattern, url, re.IGNORECASE)
    if match:
        file_id = match.group(1)
        return f"https://hubcloud.one/drive/{file_id}"
    return url

def extract_hubcloud_urls(text: str) -> list[str]:
    """Find all HubCloud or Vifix URLs in a text message."""
    patterns = [
        r"https?://hubcloud\.one/drive/[a-z0-9]+",
        r"https?://vifix\.site/hubcloud/[a-z0-9]+"
    ]
    urls = []
    for pattern in patterns:
        found = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(found)
    # Remove duplicates while preserving order
    unique = []
    for u in urls:
        if u not in unique:
            unique.append(u)
    return unique

async def fetch_html(target_url: str) -> str:
    """Fetch HTML content using direct request + CORS proxy fallback."""
    async with aiohttp.ClientSession() as session:
        # 1) Direct
        try:
            async with session.get(target_url, timeout=15, headers={"User-Agent": USER_AGENT}) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            logger.warning(f"Direct request failed: {e}")

        # 2) Proxies
        for proxy in CORS_PROXIES:
            try:
                if "allorigins.win" in proxy:
                    proxy_url = f"{proxy}{target_url}"
                    async with session.get(proxy_url, timeout=15) as resp:
                        data = await resp.json()
                        html = data.get("contents", "")
                        if html and len(html) > 200:
                            return html
                else:
                    proxy_url = f"{proxy}{target_url}"
                    async with session.get(proxy_url, timeout=15, headers={"User-Agent": USER_AGENT}) as resp:
                        html = await resp.text()
                        if html and len(html) > 200:
                            return html
            except Exception as e:
                logger.warning(f"Proxy {proxy} failed: {e}")
                continue

        raise Exception("All fetch methods failed. HubCloud may be unreachable or link is invalid.")

async def extract_direct_links(hubcloud_url: str) -> list[dict]:
    """
    Extract direct download links from a single HubCloud URL.
    Returns a list of dicts: {"url": str, "type": str, "text": str}
    """
    target_url = normalize_url(hubcloud_url)
    logger.info(f"Extracting from {target_url}")

    # Step 1 – get first page
    html1 = await fetch_html(target_url)
    soup = BeautifulSoup(html1, "html.parser")
    download_tag = soup.find("a", id="download")
    if not download_tag or not download_tag.get("href"):
        raise Exception("Download link (#download anchor) not found on page.")

    hubcloud_php = download_tag["href"]
    if hubcloud_php.startswith("/"):
        parsed = urlparse(target_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        hubcloud_php = urljoin(base, hubcloud_php)
    elif not hubcloud_php.startswith("http"):
        hubcloud_php = urljoin(target_url, hubcloud_php)

    # Step 2 – fetch hubcloud.php
    html2 = await fetch_html(hubcloud_php)
    soup2 = BeautifulSoup(html2, "html.parser")
    all_links = soup2.find_all("a", href=True)

    direct_links = []
    for link in all_links:
        href = link["href"]
        text = link.get_text(strip=True) or "Download"

        # Matching logic (same as JS version)
        if "r2.dev" in href or "cloudflare" in href:
            direct_links.append({"url": href, "text": text, "type": "Cloudflare R2"})
        elif "pixeldrain" in href:
            if "/u/" in href:
                file_id = href.split("/u/")[-1].split("?")[0].split("#")[0]
                direct_url = f"https://pixeldrain.com/api/file/{file_id}"
                direct_links.append({"url": direct_url, "text": text, "type": "PixelDrain"})
            elif "/api/file/" in href:
                direct_links.append({"url": href, "text": text, "type": "PixelDrain"})
        elif "workers.dev" in href:
            direct_links.append({"url": href, "text": text, "type": "Cloudflare Workers"})
        elif "googleusercontent.com" in href or "drive.google.com" in href:
            direct_links.append({"url": href, "text": text, "type": "Google Drive"})
        elif re.search(r"\.(zip|rar|7z|mkv|mp4|avi|mov|pdf|doc|docx)$", href, re.I):
            direct_links.append({"url": href, "text": text, "type": "Direct File"})
        elif any(service in href for service in ["mediafire", "mega.nz", "dropbox"]):
            direct_links.append({"url": href, "text": text, "type": "External Service"})

    if not direct_links:
        raise Exception("No direct download links found on the page.")
    return direct_links

def format_links_message(links: list[dict], original_url: str) -> str:
    """Create a readable Telegram message from extracted links."""
    msg = f"<b>🔗 Links extracted from:</b>\n<code>{original_url}</code>\n\n"
    for idx, link in enumerate(links, 1):
        msg += f"<b>{idx}. {link['type']}</b>\n"
        msg += f"<code>{link['url']}</code>\n"
        if link['text'] and link['text'] != "Download":
            msg += f"📄 <i>{link['text'][:60]}</i>\n"
        msg += "\n"
    msg += "👇 <i>Click any link to download</i>"
    return msg
