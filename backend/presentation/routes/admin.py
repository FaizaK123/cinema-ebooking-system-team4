"""HTTP endpoints for the administration portal."""
from flask import Blueprint, jsonify, request

from backend.application.services import admin as admin_service
from backend.infrastructure.security import current_user, login_required
from backend.presentation.presenters import service_response

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@admin_bp.get("/summary")
@login_required(role="ADMIN")
def summary():
    return service_response(admin_service.get_summary(current_user()))


# ---- Movies ----

@admin_bp.post("/movies")
@login_required(role="ADMIN")
def add_movie():
    """Multipart form: title, description, releaseDate, duration (minutes), rating, genres (repeat the field
    for each genre), optional trailer, and the poster image file in the `poster` field."""
    if request.is_json:
        data, poster = _json_body(), None
    else:
        data = request.form.to_dict()
        data["genres"] = request.form.getlist("genres")
        poster = request.files.get("poster")
    return service_response(admin_service.add_movie(data, poster))


# ---- Showrooms and showtimes ----

@admin_bp.get("/showrooms")
@login_required(role="ADMIN")
def list_showrooms():
    """Add ?date=YYYY-MM-DD&time=HH:MM to see which showrooms allow a three-hour gap around that start."""
    return service_response(admin_service.list_showrooms(request.args.get("date"), request.args.get("time")))


@admin_bp.get("/showtimes")
@login_required(role="ADMIN")
def list_showtimes():
    movie_id = request.args.get("movieId", type=int)
    if "movieId" in request.args and movie_id is None:
        return jsonify({"error": "movieId must be a number."}), 400
    return service_response(admin_service.list_showtimes(movie_id))


@admin_bp.post("/showtimes")
@login_required(role="ADMIN")
def add_showtime():
    return service_response(admin_service.add_showtime(_json_body()))


# ---- Promotions ----

@admin_bp.get("/promotions")
@login_required(role="ADMIN")
def list_promotions():
    return service_response(admin_service.list_promotions())


@admin_bp.post("/promotions")
@login_required(role="ADMIN")
def add_promotion():
    return service_response(admin_service.add_promotion(_json_body()))
