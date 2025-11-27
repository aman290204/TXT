#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from dotenv import load_dotenv
import multiprocessing


def run_app():
    """Start the Flask web app (app.py)."""
    try:
        subprocess.run([sys.executable, "app.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Web app process error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in web app process: {e}")
        sys.exit(1)


def run_bot():
    """Start the Telegram bot, ensuring a fresh Pyrogram session."""
    try:
        # Ensure sessions directory exists
        os.makedirs("sessions", exist_ok=True)
        # Remove stale Pyrogram session file if present
        session_path = os.path.join("sessions", "Extractor.session")
        if os.path.exists(session_path):
            os.remove(session_path)
            print("[INIT] Removed stale Pyrogram session file to force re-authentication")
        # Launch the bot module
        subprocess.run([sys.executable, "-m", "Extractor"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Bot process error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error in bot process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Load environment variables (local .env or Render/Heroku env)
    load_dotenv()

    # Verify required credentials
    try:
        from config import API_ID, API_HASH, BOT_TOKEN
        if not all([API_ID, API_HASH, BOT_TOKEN]):
            sys.exit("⚠️  Missing API_ID, API_HASH, or BOT_TOKEN in the environment")
    except ImportError:
        sys.exit("⚠️  config.py file not found or missing required variables")

    # Determine execution environment
    if os.environ.get('DYNO') or os.environ.get('RENDER'):
        print("Running on Render/Heroku environment")
        # Start both web app and bot as separate processes
        web_process = multiprocessing.Process(target=run_app, name="web_app")
        bot_process = multiprocessing.Process(target=run_bot, name="telegram_bot")
        web_process.start()
        bot_process.start()
        # Monitor and restart if any process dies
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
        # Local development: run bot in foreground
        try:
            run_bot()
        except KeyboardInterrupt:
            print("Bot stopped by user.")
        except Exception as e:
            print(f"Bot error: {e}")