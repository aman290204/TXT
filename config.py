import os
from os import getenv


# ------------------------------------------------
API_ID = int(os.environ.get("API_ID", "22984163"))
# ------------------------------------------------
API_HASH = os.environ.get("API_HASH","18c3760d602be96b599fa42f1c322956")
# ------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8431570808:AAGKp6nNM6qhSVsuXuzYRDCFm1xcWb7yUiU")
# ------------------------------------------------
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@Course_Downloader_bot")
BOT_TEXT = "Educational Hub Extractor"
# ------------------------------------------------
OWNER_ID = int(os.environ.get("OWNER_ID", "915101089"))
# ------------------------------------------------
# //LOG CHANNEL ID 
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003235364017"))

# //FORCE_CHANNEL_ID
CHANNEL_ID2 = int(os.environ.get("CHANNEL_ID2", "0")) if os.environ.get("CHANNEL_ID2") else None
# ------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://missioncfa8:FmHOfEe5Z9wLXOSu@cluster0.mswwysd.mongodb.net/?appName=Cluster0")
# -----------------------------------------------
PREMIUM_LOGS = int(os.environ.get("PREMIUM_LOGS", "0")) if os.environ.get("PREMIUM_LOGS") else None
# -----------------------------------------------
join = '<a href="https://t.me/RPSC_UPSC_CURRENT">✳️ JOIN BACKUP</a>'
# -----------------------------------------------
UNSPLASH_ACCESS_KEY = os.environ.get('UNSPLASH_ACCESS_KEY', '')
# -----------------------------------------------
UNSPLASH_QUERY = os.environ.get('UNSPLASH_QUERY', 'educational')
# -----------------------------------------------
ADMIN_BOT_USERNAME = os.environ.get("ADMIN_BOT_USERNAME", "") #without @

THUMB_URL = os.environ.get("THUMB_URL", "")

