#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import subprocess
import sys
import time

def run_app():
    try:
        # This assumes you have an app.py in your project root.
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Web app process error: {e}")
        sys.exit(1)

def run_bot():
    try:
        # Ensure sessions directory exists
        os.makedirs("sessions", exist_ok=True)
        
        # Launch the pyrogram/pyromod bot
        subprocess.run([sys.executable, "-m", "Extractor"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Bot process error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in bot process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 1) Load .env locally; on Render/Heroku env vars are already set
    load_dotenv()

    # 2) Verify we have the creds we need
    try:
        from config import API_ID, API_HASH, BOT_TOKEN
        if not all([API_ID, API_HASH, BOT_TOKEN]):
            sys.exit("⚠️  Missing API_ID, API_HASH, or BOT_TOKEN in the environment")
    except ImportError:
        sys.exit("⚠️  config.py file not found or missing required variables")

    # 3) Check if running on Heroku or Render (both use environment variables)
    if os.environ.get('DYNO') or os.environ.get('RENDER'):
        print("Running on Render/Heroku environment")
        # On Heroku/Render, run both bot and web app
        import multiprocessing
        print("Starting web app process...")
        web_process = multiprocessing.Process(target=run_app, name="web_app")
        web_process.start()
        
        print("Starting bot process...")
        bot_process = multiprocessing.Process(target=run_bot, name="telegram_bot")
        bot_process.start()
        
        # Monitor processes and restart if needed
        while True:
            if not web_process.is_alive():
                print("Web app process died, restarting...")
                web_process = multiprocessing.Process(target=run_app, name="web_app")
                web_process.start()
                
            if not bot_process.is_alive():
                print("Bot process died, restarting...")
                bot_process = multiprocessing.Process(target=run_bot, name="telegram_bot")
                bot_process.start()
                
            time.sleep(5)
    else:
        # Run both processes in sequence for local development
        try:
            # Run bot in foreground
            run_bot()
        except KeyboardInterrupt:
            print("Bot stopped by user.")
        except Exception as e:
            print(f"Bot error: {e}")