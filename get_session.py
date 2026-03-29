from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("Enter TG_API_ID: ").strip())
API_HASH = input("Enter TG_API_HASH: ").strip()

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n✅ LOGIN SUCCESS")
    print("\n🔐 YOUR TG_SESSION (SAVE THIS SAFELY):\n")
    print(client.session.save())