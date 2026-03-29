from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

# Put your actual IDs here
API_ID = 30119467
API_HASH = 'ab6416d4c695ceb75e2adf0b6f80c35d'

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\n--- COPY THIS ENTIRE STRING ---")
    print(client.session.save())
    print("--- END ---")