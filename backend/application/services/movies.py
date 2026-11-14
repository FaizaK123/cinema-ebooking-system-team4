"""Use cases for browsing the movie catalog and its showtimes."""
from backend.application.services.results import ServiceResult
from backend.data_access.db import get_db_connection
from backend.data_access.repositories import MovieRepository, ShowRepository
from backend.infrastructure.timeutil import local_now


def list_movies(title, genres):
    conn = get_db_connection()
    try:
        rows = MovieRepository.search(conn, title, genres)
        showings = ShowRepository.upcoming_by_movie(conn, local_now())
    finally:
        conn.close()
    return ServiceResult(rows, meta={"showings": showings})


def get_movie(movie_id):
    conn = get_db_connection()
    try:
        row = MovieRepository.find(conn, movie_id)
        showings = ShowRepository.list_upcoming_for_movie(conn, movie_id, local_now()) if row else []
    finally:
        conn.close()
    if row is None:
        return ServiceResult({"error": f"Movie {movie_id} not found"}, 404)
    return ServiceResult(row, meta={"showings": {movie_id: showings}})


def list_showtimes(movie_id):
    """Upcoming showtimes of one movie, loaded from the database (past showtimes are hidden)."""
    conn = get_db_connection()
    try:
        movie = MovieRepository.find(conn, movie_id)
        showings = ShowRepository.list_upcoming_for_movie(conn, movie_id, local_now()) if movie else []
    finally:
        conn.close()
    if movie is None:
        return ServiceResult({"error": f"Movie {movie_id} not found"}, 404)
    return ServiceResult({"movieId": movie_id, "movieTitle": movie["title"], "showtimes": showings})


def list_genres():
    conn = get_db_connection()
    try:
        genres = MovieRepository.genres(conn)
    finally:
        conn.close()
    return ServiceResult(genres)
