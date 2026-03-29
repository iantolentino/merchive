import os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession
from loguru import logger
from dotenv import load_dotenv

# --- ROBUST PATH LOGIC ---
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Env Vars
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = os.getenv("CHANNEL_ID") # This is exported for main.py
SESSION_STRING = os.getenv("TG_SESSION")

# --- SMART CLIENT LOGIC ---
if SESSION_STRING:
    logger.info("✅ Vercel Mode: Using StringSession")
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    logger.info("🏠 Local Mode: Using anon.session")
    client = TelegramClient('anon', API_ID, API_HASH)

async def ensure_connected():
    """Ensure the client is connected before any operation."""
    if not client.is_connected():
        await client.connect()
    return client

async def stream_telegram_file(message_id: str, offset: int = 0, limit: int = None):
    try:
        tg = await ensure_connected()
        # Convert CHANNEL_ID to int if it's a standard ID, else keep as string/username
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        message = await tg.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            return

        # Using offset and limit allows the browser to request small chunks
        async for chunk in tg.iter_download(
            message.media,
            offset=offset,
            limit=limit,
            request_size=256 * 1024, # 256KB chunks are most stable for Vercel
            buffer_size=1 * 1024 * 1024 # 1MB pre-fetch to keep stream smooth
        ):
            if chunk:
                yield chunk
    except Exception as e:
        logger.error(f"Stream Error: {e}")