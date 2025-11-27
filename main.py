import sys
import subprocess

if __name__ == "__main__":
    # Launch the pyrogram/pyromod bot
    try:
        subprocess.run([sys.executable, "-m", "Extractor"], check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error starting bot: {e}")
