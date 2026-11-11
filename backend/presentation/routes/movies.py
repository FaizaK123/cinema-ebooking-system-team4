"""HTTP endpoints for the public movie catalog."""
from flask import Blueprint, request

from backend.application.services import movies as movie_service
from backend.presentation.presenters import movies_response, service_response

movies_bp = Blueprint("movies", __name__)


@movies_bp.route("/api/movies")
def get_movies_json():
    result = movie_service.list_movies(
        request.args.get("title"), request.args.getlist("genre")
    )
    return movies_response(result)


@movies_bp.route("/api/movies/<int:movie_id>")
def get_movie_by_id(movie_id):
    result = movie_service.get_movie(movie_id)
    if result.status != 200:
        return service_response(result)
    return movies_response(result, single=True)


@movies_bp.route("/api/genres")
def get_genres():
    return service_response(movie_service.list_genres())
