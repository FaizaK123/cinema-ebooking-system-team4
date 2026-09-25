import os
from flask import Flask, send_from_directory, jsonify
import sqlite3
from datetime import date, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
DB_PATH = os.path.join(BASE_DIR, "movies.db")
SHOWTIMES = ["2:00 PM", "5:00 PM", "8:00 PM"]

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def build_showtimes():
    return {
        (date.today() + timedelta(days=i)).isoformat(): SHOWTIMES
        for i in range(14)
    }

def row_to_movie(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "releaseDate": row["release_date"],
        "rating": row["rating"],
        "runtime": row["runtime"],
        "isCurrent": row["status"] == "CURRENTLY_RUNNING",
        "genre": row["genre"],
        "description": row["description"],
        "trailer": row["trailer"],
        "poster": row["poster"],
        "showtimes": build_showtimes() if row["status"] == "CURRENTLY_RUNNING" else {}
    }

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "Home_Page.html")

@app.route("/api/movies")
def get_movies_json():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies")
    rows = cursor.fetchall()
    movies = [row_to_movie(row) for row in rows]
    conn.close()
    return jsonify(movies)                


if __name__ == "__main__":
    app.run(debug=True)
