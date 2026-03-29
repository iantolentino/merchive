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
# If TG_SESSION exists (Vercel), use it. Otherwise, use local 'anon' session.
if SESSION_STRING:
    logger.info("Using StringSession for Vercel/Production")
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    logger.info("Using local 'anon.session' file for testing")
    client = TelegramClient('anon', API_ID, API_HASH)

async def ensure_connected():
    """Ensure the client is connected before any operation."""
    if not client.is_connected():
        # StringSession doesn't need bot_token if you logged in as a User
        await client.connect()
    return client

async def stream_telegram_file(message_id: str):
    """Streams the raw video file from the Telegram channel."""
    try:
        tg = await ensure_connected()
        
        # Format Channel ID correctly
        # If it's a string like '-100...', turn it into an int
        target = int(CHANNEL_ID) if str(CHANNEL_ID).startswith('-100') else CHANNEL_ID
        
        # 1. Get the message object
        message = await tg.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            logger.error(f"❌ MEDIA_NOT_FOUND: Message {message_id}")
            return

        logger.info(f"🎥 STREAMING_START: Message {message_id}")
        
        # 2. Iterate through chunks
        # 128KB - 256KB is better for Vercel to avoid timeouts compared to 1MB chunks
        async for chunk in tg.iter_download(
            message.media, 
            request_size=256 * 1024 
        ):
            if chunk:
                yield chunk
                
    except Exception as e:
        logger.error(f"🚨 STREAM_ERROR: {e}")