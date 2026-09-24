import os
from flask import Flask, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "Home_Page.html")

if __name__ == "__main__":
    app.run(debug=True)

