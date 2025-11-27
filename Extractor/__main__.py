import asyncio
import importlib
import signal
import sys
from pyrogram import idle
from Extractor.modules import ALL_MODULES

loop = asyncio.get_event_loop()

# Graceful shutdown
should_exit = asyncio.Event()

def shutdown():
    print("Shutting down gracefully...")
    should_exit.set()  # triggers exit from idle

# Handle SIGTERM and SIGINT
def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    shutdown()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

async def sumit_boot():
    # Import the app and global variables from __init__
    from Extractor import app
    import Extractor
    
    # Start the bot first
    await app.start()
    
    # Fetch bot info and set global variables
    getme = await app.get_me()
    Extractor.BOT_ID = getme.id
    Extractor.BOT_USERNAME = getme.username
    if getme.last_name:
        Extractor.BOT_NAME = getme.first_name + " " + getme.last_name
    else:
        Extractor.BOT_NAME = getme.first_name
    
    print(f"Bot started as {Extractor.BOT_NAME} (@{Extractor.BOT_USERNAME})")
    
    # Now load all modules
    for all_module in ALL_MODULES:
        importlib.import_module("Extractor.modules." + all_module)

    print("» ʙᴏᴛ ᴅᴇᴘʟᴏʏ sᴜᴄᴄᴇssғᴜʟʟʏ ✨ 🎉")
    await idle()  # keeps the bot alive

    print("» ɢᴏᴏᴅ ʙʏᴇ ! sᴛᴏᴘᴘɪɴɢ ʙᴏᴛ.")

if __name__ == "__main__":
    try:
        loop.run_until_complete(sumit_boot())
    except KeyboardInterrupt:
        print("Interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Cancel pending tasks to avoid "destroyed but pending" error
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except:
            pass
        loop.close()
        print("Loop closed.")