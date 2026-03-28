import os
from pathlib import Path
from telethon import TelegramClient
from loguru import logger
from dotenv import load_dotenv

# --- ROBUST PATH LOGIC ---
dotenv_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)

API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Initialize Client
client = TelegramClient('bot_session', API_ID, API_HASH)

async def get_tg_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
    return client

async def stream_telegram_file(message_id: str):
    """Streams the raw video file from the Telegram channel."""
    tg = await get_tg_client()
    try:
        # Force Channel ID to integer
        target = int(str(CHANNEL_ID))
        message = await tg.get_messages(target, ids=int(message_id))
        
        if not message or not message.media:
            logger.error(f"❌ MEDIA_NOT_FOUND: Message {message_id}")
            return

        logger.info(f"🎥 STREAMING_START: Message {message_id}")
        
        async for chunk in tg.iter_download(message.media, chunk_size=1024*1024):
            if chunk:
                yield chunk
                
    except Exception as e:
        logger.error(f"🚨 STREAM_ERROR: {e}")