"""Movie catalog API (Sprint 1): list/search/filter movies, one movie, genres."""
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from db import get_db_connection
from repositories import MovieRepository

movies_bp = Blueprint("movies", __name__)

SHOWTIMES = ["2:00 PM", "5:00 PM", "8:00 PM"]


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


@movies_bp.route("/api/movies")
def get_movies_json():
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    title = request.args.get("title")
    if title:
        conditions.append("title LIKE ?")
        params.append(f"%{title}%")

    genres = request.args.getlist("genre")
    if genres:
        placeholders = ", ".join("?" for _ in genres)
        conditions.append(f"LOWER(genre) IN ({placeholders})")
        params.extend(g.lower() for g in genres)

    query = "SELECT * FROM movies"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    movies = [row_to_movie(row) for row in rows]
    conn.close()
    return jsonify(movies)


@movies_bp.route("/api/movies/<int:movie_id>")
def get_movie_by_id(movie_id):
    conn = get_db_connection()
    row = MovieRepository.find(conn, movie_id)
    conn.close()

    if row is None:
        return jsonify({"error": f"Movie {movie_id} not found"}), 404

    return jsonify(row_to_movie(row))


@movies_bp.route("/api/genres")
def get_genres():
    conn = get_db_connection()
    genres = MovieRepository.genres(conn)
    conn.close()
    return jsonify(genres)
