"""Use cases for browsing the movie catalog."""
from backend.application.services.results import ServiceResult
from backend.data_access.db import get_db_connection
from backend.data_access.repositories import MovieRepository


def list_movies(title, genres):
    conn = get_db_connection()
    try:
        rows = MovieRepository.search(conn, title, genres)
    finally:
        conn.close()
    return ServiceResult(rows)


def get_movie(movie_id):
    conn = get_db_connection()
    try:
        row = MovieRepository.find(conn, movie_id)
    finally:
        conn.close()
    if row is None:
        return ServiceResult({"error": f"Movie {movie_id} not found"}, 404)
    return ServiceResult(row)


def list_genres():
    conn = get_db_connection()
    try:
        genres = MovieRepository.genres(conn)
    finally:
        conn.close()
    return ServiceResult(genres)
