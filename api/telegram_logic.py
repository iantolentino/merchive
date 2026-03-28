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
    tg = await get_tg_client()
    try:
        # 1. Fetch the message from your channel
        message = await tg.get_messages(CHANNEL_ID, ids=int(message_id))
        
        if not message or not message.media:
            logger.error(f"❌ No media found in Telegram message ID: {message_id}")
            return

        logger.info(f"🎥 Starting stream: Message {message_id}")

        # 2. Use iter_download but point directly to the media object
        # This is the most stable way to stream to a browser
        async for chunk in tg.iter_download(message.media, chunk_size=1024*1024):
            if chunk:
                yield chunk
            
    except Exception as e:
        logger.error(f"🚨 Telegram Streaming Error: {e}")

async def get_video_thumbnail(message_id: str):
    tg = await get_tg_client()
    try:
        message = await tg.get_messages(CHANNEL_ID, ids=int(message_id))
        
        if not message or not message.media:
            return None

        # 1. Try standard video thumbnails
        if hasattr(message, 'video') and message.video and message.video.thumbs:
            return await tg.download_media(message.video.thumbs[-1], file=bytes)

        # 2. Try document (file) thumbnails
        if hasattr(message.media, 'document') and message.media.document.thumbs:
            return await tg.download_media(message.media.document.thumbs[-1], file=bytes)

        # 3. Final Catch-All: Try downloading a 'thumb' version of the media itself
        # This works if Telegram generated a generic preview
        return await tg.download_media(message.media, file=bytes, thumb=-1)
        
    except Exception as e:
        logger.error(f"🚨 Thumbnail Error for Msg {message_id}: {e}")
        return None