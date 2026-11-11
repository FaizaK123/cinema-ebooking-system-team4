"""Convert application and repository results into HTTP response bodies."""
from datetime import date, timedelta

from flask import jsonify


SHOWTIMES = ["2:00 PM", "5:00 PM", "8:00 PM"]


def build_showtimes():
    return {
        (date.today() + timedelta(days=index)).isoformat(): SHOWTIMES
        for index in range(14)
    }


def movie_to_dict(row):
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
        "showtimes": build_showtimes() if row["status"] == "CURRENTLY_RUNNING" else {},
    }


def service_response(result):
    return jsonify(result.data), result.status


def movies_response(result, single=False):
    if result.status != 200:
        return service_response(result)
    if single:
        return jsonify(movie_to_dict(result.data)), result.status
    return jsonify([movie_to_dict(row) for row in result.data]), result.status
