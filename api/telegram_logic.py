import os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from loguru import logger
from dotenv import load_dotenv

# --- PATH SETUP ---
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SESSION_STRING = os.getenv("TG_SESSION")

# --- CLIENT LOGIC ---
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient('anon', API_ID, API_HASH)

async def ensure_connected():
    if not client.is_connected():
        await client.connect()
    return client

async def stream_telegram_file(message_id: int, offset: int = 0, limit: int = None):
    """
    FIXED: Now properly handles Byte-Ranges.
    This allows the browser to request the video in 1MB chunks
    without the connection timing out.
    """
    try:
        tg = await ensure_connected()
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        # Get the specific message
        message = await tg.get_messages(target, ids=message_id)
        
        if not message or not message.media:
            logger.error(f"No media found for ID {message_id}")
            return

        # CRITICAL FIX: iter_download MUST use offset and limit
        async for chunk in tg.iter_download(
            message.media,
            offset=offset,      # Start at this byte
            limit=limit,        # Only download this many bytes
            request_size=128 * 1024, # 128KB chunks for better flow
        ):
            if chunk:
                yield chunk
    except Exception as e:
        logger.error(f"Telethon Stream Error: {e}")