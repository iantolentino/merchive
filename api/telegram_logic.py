import os
from pathlib import Path
from telethon import TelegramClient
from telethon.sessions import StringSession # Don't forget this import!
from loguru import logger
from dotenv import load_dotenv

# --- ROBUST PATH LOGIC ---
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Env Vars
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = os.getenv("CHANNEL_ID")
SESSION_STRING = os.getenv("TG_SESSION") # Added this!

# --- SMART CLIENT LOGIC ---
if SESSION_STRING:
    logger.info("✅ Vercel Mode: Using StringSession")
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    logger.info("🏠 Local Mode: Using anon.session")
    client = TelegramClient('anon', API_ID, API_HASH)

async def ensure_connected():
    if not client.is_connected():
        await client.connect()
    return client

async def stream_telegram_file(message_id: str):
    try:
        tg = await ensure_connected()
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        message = await tg.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            return

        async for chunk in tg.iter_download(
            message.media, 
            request_size=512 * 1024 # Increased to 512KB for faster filling of the buffer
        ):
            if chunk:
                yield chunk
    except Exception as e:
        logger.error(f"Stream Error: {e}")

async def ensure_connected():
    """Ensure the client is connected before any operation."""
    if not client.is_connected():
        # StringSession doesn't need bot_token if you logged in as a User
        await client.connect()
    return client

async def stream_telegram_file(message_id: str):
    try:
        tg = await ensure_connected()
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        message = await tg.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            return

        # 256KB is the "Safe Zone" for Vercel Free Tier
        async for chunk in tg.iter_download(
            message.media, 
            request_size=256 * 1024, 
            buffer_size=1 * 1024 * 1024 # Pre-fetches 1MB to stay ahead
        ):
            if chunk:
                yield chunk
    except Exception as e:
        logger.error(f"Stream Error: {e}")