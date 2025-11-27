import asyncio
import logging
import os
from pyromod import listen
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

# Create sessions directory if it doesn't exist
if not os.path.exists("sessions"):
    os.makedirs("sessions")

loop = asyncio.get_event_loop()

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)

app = Client(
    "Extractor",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions",
    workers=200,
)

# Initialize pyromod attributes
app.listening = {}
app.listening_cb = {}
app.waiting_input = {}

# Global bot info variables (will be set by __main__.py after app.start())
BOT_ID = None
BOT_NAME = None
BOT_USERNAME = None
