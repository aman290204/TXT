import os
import sys
from flask import Flask, Response

LOG_FILE = "/opt/render/project/src/app_logs.txt"

# Custom log writer to duplicate logs to a file
class LogWriter:
    def __init__(self, stream):
        self.stream = stream

    def write(self, message):
        # Write to normal stdout
        self.stream.write(message)
        self.stream.flush()

        # Append message to log file
        try:
            with open(LOG_FILE, "a") as f:
                f.write(message)
        except:
            pass

    def flush(self):
        self.stream.flush()

# Override stdout and stderr
sys.stdout = LogWriter(sys.stdout)
sys.stderr = LogWriter(sys.stderr)

def create_app():
    app = Flask(__name__)
    
    @app.route("/")
    def home():
        print("Home page visited")
        return "Hello, Render!"
    
    @app.route("/logs")
    def show_logs():
        try:
            if not os.path.exists(LOG_FILE):
                return "Log file not found", 404

            # Read only the last 2000 lines
            lines = []
            with open(LOG_FILE, "rb") as f:
                try:
                    f.seek(-100000, os.SEEK_END) # Go back ~100KB
                except OSError:
                    f.seek(0) # File is smaller than 100KB
                
                lines = f.readlines()
                
            # Decode and join the last 2000 lines
            decoded_lines = [line.decode('utf-8', errors='ignore') for line in lines]
            return Response("".join(decoded_lines[-2000:]), mimetype="text/plain")
        except Exception as e:
            return Response("Error reading logs file:\n" + str(e), status=500)

    return app

app = create_app()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=PORT, debug=False)
