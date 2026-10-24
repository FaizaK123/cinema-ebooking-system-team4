"""Edit profile: personal info, password, address, payment cards, favorites and genre preferences.

Every route here requires a logged-in CUSTOMER, and always acts on the logged-in
user's own data (the user id comes from the session, never from the request).
"""
from flask import Blueprint, jsonify, request

import config
from db import db_transaction, get_db_connection
from email_service import EmailService
from repositories import AddressRepository, CardRepository, FavoriteRepository, MovieRepository, UserRepository
from routes.movies import row_to_movie
from security import current_user, encrypt_card_number, hash_password, login_required, verify_password
from validators import validate_address, validate_card, validate_name, validate_password, validate_phone

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _errors_response(errors):
    return jsonify({"error": "Please fix the highlighted fields.", "errors": errors}), 400


def _notify(user, changes):
    """Security requirement: email the user whenever their personal information changes."""
    if changes:
        EmailService.send_account_change(user.first_name, user.email, changes)


# ---------------------------------------------------------------- Profile

@profile_bp.get("")
@login_required(role="CUSTOMER")
def get_profile():
    user = current_user()
    conn = get_db_connection()
    try:
        address = AddressRepository.get(conn, user.id)
        cards = CardRepository.list(conn, user.id)
    finally:
        conn.close()
    return jsonify({
        **user.to_public_dict(),
        "address": address,
        "cards": cards,
        "maxCards": config.MAX_PAYMENT_CARDS,
    })


@profile_bp.put("")
@login_required(role="CUSTOMER")
def update_profile():
    user = current_user()
    data = _json_body()
    errors = {}

    if "email" in data and str(data["email"]).strip().lower() != user.email:
        errors["email"] = "Your email address can't be changed."
    first_name, err = validate_name(data.get("firstName"), "First name")
    if err: errors["firstName"] = err
    last_name, err = validate_name(data.get("lastName"), "Last name")
    if err: errors["lastName"] = err
    phone, err = validate_phone(data.get("phone"))
    if err: errors["phone"] = err
    promo_opt_in = bool(data.get("promoOptIn"))

    conn = get_db_connection()
    try:
        other = UserRepository.find_by_phone(conn, phone) if "phone" not in errors else None
        if other and other.id != user.id:
            errors["phone"] = "This phone number is already linked to another account."
    finally:
        conn.close()
    if errors:
        return _errors_response(errors)

    changes = []
    if first_name != user.first_name:
        changes.append("First name updated")
    if last_name != user.last_name:
        changes.append("Last name updated")
    if phone != user.phone:
        changes.append("Phone number updated")
    if promo_opt_in != user.promo_opt_in:
        changes.append("Promotion emails turned " + ("on" if promo_opt_in else "off"))

    if not changes:
        return jsonify({"message": "No changes to save."})

    with db_transaction() as conn:
        UserRepository.update_profile(conn, user.id, first_name, last_name, phone, promo_opt_in)
    _notify(user, changes)
    return jsonify({"message": "Your profile has been updated. We emailed you a confirmation of the changes."})


@profile_bp.put("/password")
@login_required(role="CUSTOMER")
def change_password():
    user = current_user()
    data = _json_body()
    errors = {}

    current_password = data.get("currentPassword") or ""
    if not current_password:
        errors["currentPassword"] = "Enter your current password."
    elif not verify_password(user.password_hash, current_password):
        errors["currentPassword"] = "Your current password is incorrect."

    new_password, err = validate_password(data.get("newPassword"))
    if err:
        errors["newPassword"] = err
    elif current_password and new_password == current_password:
        errors["newPassword"] = "Your new password must be different from your current password."
    if data.get("confirmPassword") != data.get("newPassword"):
        errors["confirmPassword"] = "Passwords don't match."
    if errors:
        return _errors_response(errors)

    with db_transaction() as conn:
        UserRepository.update_password(conn, user.id, hash_password(new_password))
    _notify(user, ["Password changed"])
    return jsonify({"message": "Your password has been changed."})


# ---------------------------------------------------------------- Address (max one)

@profile_bp.put("/address")
@login_required(role="CUSTOMER")
def save_address():
    user = current_user()
    address, errors = validate_address(_json_body())
    if errors:
        return _errors_response(errors)
    with db_transaction() as conn:
        had_address = AddressRepository.get(conn, user.id) is not None
        AddressRepository.save(conn, user.id, address)
    _notify(user, ["Home address " + ("updated" if had_address else "added")])
    return jsonify({"message": "Your address has been saved.", "address": address})


@profile_bp.delete("/address")
@login_required(role="CUSTOMER")
def delete_address():
    user = current_user()
    with db_transaction() as conn:
        removed = AddressRepository.delete(conn, user.id)
    if not removed:
        return jsonify({"error": "There is no saved address to remove."}), 404
    _notify(user, ["Home address removed"])
    return jsonify({"message": "Your address has been removed."})


# ---------------------------------------------------------------- Payment cards (max three)

@profile_bp.get("/cards")
@login_required(role="CUSTOMER")
def list_cards():
    user = current_user()
    conn = get_db_connection()
    try:
        cards = CardRepository.list(conn, user.id)
    finally:
        conn.close()
    return jsonify({"cards": cards, "maxCards": config.MAX_PAYMENT_CARDS})


@profile_bp.post("/cards")
@login_required(role="CUSTOMER")
def add_card():
    user = current_user()
    card, errors = validate_card(_json_body())
    with db_transaction() as conn:
        if CardRepository.count(conn, user.id) >= config.MAX_PAYMENT_CARDS:
            return jsonify({
                "error": f"You can save up to {config.MAX_PAYMENT_CARDS} payment cards. Remove one to add another.",
                "code": "CARD_LIMIT",
            }), 400
        if errors:
            return _errors_response(errors)
        CardRepository.add(conn, user.id, card, encrypt_card_number(card["number"]))
    _notify(user, [f"{card['brand']} card ending in {card['number'][-4:]} added"])
    return jsonify({"message": f"Your {card['brand']} card ending in {card['number'][-4:]} has been saved."}), 201


@profile_bp.delete("/cards/<int:card_id>")
@login_required(role="CUSTOMER")
def delete_card(card_id):
    user = current_user()
    with db_transaction() as conn:
        card = next((c for c in CardRepository.list(conn, user.id) if c["id"] == card_id), None)
        removed = card is not None and CardRepository.delete(conn, user.id, card_id)
    if not removed:
        return jsonify({"error": "That card wasn't found on your account."}), 404
    _notify(user, [f"{card['brand']} card ending in {card['lastFour']} removed"])
    return jsonify({"message": "The card has been removed."})


# ---------------------------------------------------------------- Favorite movies

@profile_bp.get("/favorites")
@login_required(role="CUSTOMER")
def list_favorites():
    user = current_user()
    conn = get_db_connection()
    try:
        movies = [row_to_movie(row) for row in FavoriteRepository.list_movies(conn, user.id)]
    finally:
        conn.close()
    return jsonify(movies)


@profile_bp.post("/favorites")
@login_required(role="CUSTOMER")
def add_favorite():
    user = current_user()
    movie_id = _json_body().get("movieId")
    if not isinstance(movie_id, int):
        return jsonify({"error": "A valid movie is required."}), 400
    with db_transaction() as conn:
        movie = MovieRepository.find(conn, movie_id)
        if movie is None:
            return jsonify({"error": "That movie wasn't found."}), 404
        FavoriteRepository.add_movie(conn, user.id, movie_id)
    return jsonify({"message": f"{movie['title']} was added to your favorites."}), 201


@profile_bp.delete("/favorites/<int:movie_id>")
@login_required(role="CUSTOMER")
def remove_favorite(movie_id):
    user = current_user()
    with db_transaction() as conn:
        movie = MovieRepository.find(conn, movie_id)
        FavoriteRepository.remove_movie(conn, user.id, movie_id)
    title = movie["title"] if movie else "The movie"
    return jsonify({"message": f"{title} was removed from your favorites."})


# ---------------------------------------------------------------- Movie preferences (favorite genres)

@profile_bp.get("/genres")
@login_required(role="CUSTOMER")
def get_genre_preferences():
    user = current_user()
    conn = get_db_connection()
    try:
        selected = FavoriteRepository.list_genres(conn, user.id)
        available = MovieRepository.genres(conn)
    finally:
        conn.close()
    return jsonify({"genres": selected, "available": available})


@profile_bp.put("/genres")
@login_required(role="CUSTOMER")
def save_genre_preferences():
    user = current_user()
    genres = _json_body().get("genres")
    if not isinstance(genres, list):
        return jsonify({"error": "Genres must be a list."}), 400
    with db_transaction() as conn:
        available = set(MovieRepository.genres(conn))
        unknown = [g for g in genres if g not in available]
        if unknown:
            return jsonify({"error": f"Unknown genre: {unknown[0]}"}), 400
        FavoriteRepository.replace_genres(conn, user.id, sorted(set(genres)))
    return jsonify({"message": "Your movie preferences have been saved."})
