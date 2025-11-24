#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import subprocess
import sys
import threading
import time

def run_app():
    print("🌐 Starting Web App...", flush=True)
    try:
        # This assumes you have an app.py in your project root.
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Web app process error: {e}", flush=True)
        # We don't exit here because we want the bot to keep running if possible,
        # but on Render this will likely cause a port binding failure.
    except Exception as e:
        print(f"❌ Unexpected error in web app: {e}", flush=True)

def run_bot():
    print("🤖 Starting Telegram Bot...", flush=True)
    try:
        # Ensure sessions directory exists
        os.makedirs("sessions", exist_ok=True)
        
        # Launch the pyrogram/pyromod bot
        subprocess.run([sys.executable, "-m", "Extractor"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Bot process error: {e}", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error in bot process: {e}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    # 1) Load .env locally; on Heroku/Render this is a no-op since env vars are already set
    load_dotenv()

    # 2) Verify we have the creds we need
    from config import API_ID, API_HASH, BOT_TOKEN
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        sys.exit("⚠️  Missing API_ID, API_HASH, or BOT_TOKEN in the environment")

    # 3) Check if running on Heroku or Render
    # On Render, we MUST run the web app to bind the port.
    # On Heroku, 'DYNO' is set.
    
    print("🚀 Starting Services...", flush=True)
    
    # Create threads for both services
    # We use threads instead of multiprocessing to share stdout/stderr easily and avoid fork issues
    web_thread = threading.Thread(target=run_app, name="web_app", daemon=True)
    bot_thread = threading.Thread(target=run_bot, name="telegram_bot", daemon=True)

    # Start both
    web_thread.start()
    bot_thread.start()

    # Keep the main thread alive and monitor
    try:
        while True:
            time.sleep(1)
            if not web_thread.is_alive():
                print("⚠️ Web App thread died!", flush=True)
                # If web app dies on Render, we should probably exit to restart the container
                sys.exit(1)
            if not bot_thread.is_alive():
                print("⚠️ Bot thread died!", flush=True)
                sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Stopping services...", flush=True)
