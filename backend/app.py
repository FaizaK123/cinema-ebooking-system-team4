import os
from flask import Flask, send_from_directory
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


FAKE_MOVIES = [
    {"id": 1, "title": "Jaws", "genre": "Horror", "rating": "PG", "description": "shark", "poster": "image path or url", "trailer": "yt trailer", "status": "currently running or coming soon"},
    {"id": 2, "title": "Annabelle", "genre": "Horror", "rating": "R", "description": "doll", "poster": "image path or url", "trailer": "yt trailer", "status": "currently running or coming soon"},
]

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "Home_Page.html")

@app.route("/api/movies")
def get_movies():
    


if __name__ == "__main__":
    app.run(debug=True)
