"""HTTP endpoints for the signed-in customer's profile and preferences."""
from flask import Blueprint, request

from backend.application.services import profile as profile_service
from backend.infrastructure.security import current_user, login_required
from backend.presentation.presenters import movies_response, service_response

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@profile_bp.get("")
@login_required(role="CUSTOMER")
def get_profile():
    return service_response(profile_service.get_profile(current_user()))


@profile_bp.put("")
@login_required(role="CUSTOMER")
def update_profile():
    return service_response(
        profile_service.update_profile(current_user(), _json_body())
    )


@profile_bp.put("/password")
@login_required(role="CUSTOMER")
def change_password():
    return service_response(
        profile_service.change_password(current_user(), _json_body())
    )


@profile_bp.put("/address")
@login_required(role="CUSTOMER")
def save_address():
    return service_response(
        profile_service.save_address(current_user(), _json_body())
    )


@profile_bp.delete("/address")
@login_required(role="CUSTOMER")
def delete_address():
    return service_response(profile_service.delete_address(current_user()))


@profile_bp.get("/cards")
@login_required(role="CUSTOMER")
def list_cards():
    return service_response(profile_service.list_cards(current_user()))


@profile_bp.post("/cards")
@login_required(role="CUSTOMER")
def add_card():
    return service_response(
        profile_service.add_card(current_user(), _json_body())
    )


@profile_bp.delete("/cards/<int:card_id>")
@login_required(role="CUSTOMER")
def delete_card(card_id):
    return service_response(
        profile_service.delete_card(current_user(), card_id)
    )


@profile_bp.get("/favorites")
@login_required(role="CUSTOMER")
def list_favorites():
    result = profile_service.list_favorites(current_user())
    return movies_response(result)


@profile_bp.post("/favorites")
@login_required(role="CUSTOMER")
def add_favorite():
    movie_id = _json_body().get("movieId")
    return service_response(
        profile_service.add_favorite(current_user(), movie_id)
    )


@profile_bp.delete("/favorites/<int:movie_id>")
@login_required(role="CUSTOMER")
def remove_favorite(movie_id):
    return service_response(
        profile_service.remove_favorite(current_user(), movie_id)
    )


@profile_bp.get("/genres")
@login_required(role="CUSTOMER")
def get_genre_preferences():
    return service_response(
        profile_service.get_genre_preferences(current_user())
    )


@profile_bp.put("/genres")
@login_required(role="CUSTOMER")
def save_genre_preferences():
    genres = _json_body().get("genres")
    return service_response(
        profile_service.save_genre_preferences(current_user(), genres)
    )
