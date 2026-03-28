import os
from telethon import TelegramClient
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# These must be in your local .env file
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("TG_CHANNEL_ID"))

# Initialize the client
client = TelegramClient('vesta_session', API_ID, API_HASH)

async def get_tg_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
    return client

async def stream_telegram_file(message_id: str):
    """
    The 'Pipe': It fetches a video from Telegram by ID 
    and yields it in 1MB chunks to the frontend.
    """
    tg = await get_tg_client()
    try:
        message = await tg.get_messages(CHANNEL_ID, ids=int(message_id))
        
        if not message or not message.file:
            logger.error(f"No file found in Telegram for ID: {message_id}")
            yield b""
            return

        # Stream the file data so it plays instantly
        async for chunk in tg.iter_download(message.file, chunk_size=1024*1024):
            yield chunk
            
    except Exception as e:
        logger.error(f"Telegram Streaming Error: {e}")
        yield b""