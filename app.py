import os
from flask import Flask

app = Flask(__name__)
print("✅ app.py is initializing...", flush=True)
PORT = int(os.environ.get("PORT", 5000))

@app.route("/")
def home():
    return "Hello, Render!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
