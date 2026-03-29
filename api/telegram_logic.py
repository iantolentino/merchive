import os
import sys
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from loguru import logger
from dotenv import load_dotenv

# --- PATH SETUP ---
# Ensures .env is found regardless of where the script is started
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SESSION_STRING = os.getenv("TG_SESSION")

# --- CLIENT INITIALIZATION ---
if SESSION_STRING:
    # StringSession is required for cloud environments like Railway
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient('anon', API_ID, API_HASH)

async def ensure_connected():
    """Maintain a persistent connection to Telegram."""
    if not client.is_connected():
        await client.connect()
    return client

async def stream_telegram_file(message_id: int, offset: int = 0, limit: int = None):
    """
    Core streaming generator.
    offset: Start byte (for seeking)
    limit: Number of bytes to fetch (for chunking)
    """
    try:
        tg = await ensure_connected()
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        # Fetch the specific message containing the video
        message = await tg.get_messages(target, ids=message_id)
        
        if not message or not message.media:
            logger.error(f"No media found for message ID {message_id}")
            return

        # iter_download is the magic that streams without saving to disk
        async for chunk in tg.iter_download(
            message.media,
            offset=offset,
            limit=limit,
            request_size=256 * 1024, # 256KB chunks balance speed and stability
        ):
            if chunk:
                yield chunk
    except Exception as e:
        logger.error(f"Telethon Stream Error: {e}")