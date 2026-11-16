"""Convert application and repository results into HTTP response bodies."""
from flask import jsonify


def group_showtimes_by_date(showings):
    """[{date, timeLabel, ...}] -> {"2026-11-20": ["2:00 PM", "5:00 PM"]} (the shape the movie page reads)."""
    grouped = {}
    for showing in showings:
        grouped.setdefault(showing["date"], []).append(showing["timeLabel"])
    return grouped


def movie_to_dict(row, showings=()):
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
        # Real showtimes from the database. `showtimes` groups the times by date; `showings` lists each
        # one with its showId and showroom (use showId to start a booking).
        "showtimes": group_showtimes_by_date(showings),
        "showings": list(showings),
    }


def service_response(result):
    return jsonify(result.data), result.status


def movies_response(result, single=False):
    if result.status != 200:
        return service_response(result)
    showings = (result.meta or {}).get("showings", {})
    if single:
        row = result.data
        return jsonify(movie_to_dict(row, showings.get(row["id"], ()))), result.status
    return jsonify([movie_to_dict(row, showings.get(row["id"], ())) for row in result.data]), result.status
