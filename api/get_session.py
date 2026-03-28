from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 123456 # Your API ID
api_hash = 'your_hash'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("YOUR_NEW_SESSION_STRING:")
    print(client.session.save())