"""Customer profile, payment, and preference use cases."""
from backend.data_access.db import db_transaction, get_db_connection
from backend.data_access.repositories import (
    AddressRepository,
    CardRepository,
    FavoriteRepository,
    MovieRepository,
    UserRepository,
)
from backend.application.services.results import ServiceResult
from backend.infrastructure import config
from backend.infrastructure.email_service import EmailService
from backend.infrastructure.security import encrypt_card_number, hash_password, verify_password
from backend.infrastructure.validators import (
    validate_address,
    validate_card,
    validate_name,
    validate_password,
    validate_phone,
)


def _errors_result(errors):
    return ServiceResult({"error": "Please fix the highlighted fields.", "errors": errors}, 400)


def _notify(user, changes):
    if changes:
        EmailService.send_account_change(user.first_name, user.email, changes)


def get_profile(user):
    conn = get_db_connection()
    try:
        address = AddressRepository.get(conn, user.id)
        cards = CardRepository.list(conn, user.id)
    finally:
        conn.close()
    return ServiceResult({
        **user.to_public_dict(),
        "address": address,
        "cards": cards,
        "maxCards": config.MAX_PAYMENT_CARDS,
    })


def update_profile(user, data):
    errors = {}
    if "email" in data and str(data["email"]).strip().lower() != user.email:
        errors["email"] = "Your email address can't be changed."
    first_name, err = validate_name(data.get("firstName"), "First name")
    if err:
        errors["firstName"] = err
    last_name, err = validate_name(data.get("lastName"), "Last name")
    if err:
        errors["lastName"] = err
    phone, err = validate_phone(data.get("phone"))
    if err:
        errors["phone"] = err
    promo_opt_in = bool(data.get("promoOptIn"))

    conn = get_db_connection()
    try:
        other = UserRepository.find_by_phone(conn, phone) if "phone" not in errors else None
        if other and other.id != user.id:
            errors["phone"] = "This phone number is already linked to another account."
    finally:
        conn.close()
    if errors:
        return _errors_result(errors)

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
        return ServiceResult({"message": "No changes to save."})

    with db_transaction() as conn:
        UserRepository.update_profile(conn, user.id, first_name, last_name, phone, promo_opt_in)
    _notify(user, changes)
    return ServiceResult({
        "message": "Your profile has been updated. We emailed you a confirmation of the changes."
    })


def change_password(user, data):
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
        return _errors_result(errors)

    with db_transaction() as conn:
        UserRepository.update_password(conn, user.id, hash_password(new_password))
    _notify(user, ["Password changed"])
    return ServiceResult({"message": "Your password has been changed."})


def save_address(user, data):
    address, errors = validate_address(data)
    if errors:
        return _errors_result(errors)
    with db_transaction() as conn:
        had_address = AddressRepository.get(conn, user.id) is not None
        AddressRepository.save(conn, user.id, address)
    _notify(user, ["Home address " + ("updated" if had_address else "added")])
    return ServiceResult({"message": "Your address has been saved.", "address": address})


def delete_address(user):
    with db_transaction() as conn:
        removed = AddressRepository.delete(conn, user.id)
    if not removed:
        return ServiceResult({"error": "There is no saved address to remove."}, 404)
    _notify(user, ["Home address removed"])
    return ServiceResult({"message": "Your address has been removed."})


def list_cards(user):
    conn = get_db_connection()
    try:
        cards = CardRepository.list(conn, user.id)
    finally:
        conn.close()
    return ServiceResult({"cards": cards, "maxCards": config.MAX_PAYMENT_CARDS})


def add_card(user, data):
    card, errors = validate_card(data)
    with db_transaction() as conn:
        if CardRepository.count(conn, user.id) >= config.MAX_PAYMENT_CARDS:
            return ServiceResult({
                "error": (
                    f"You can save up to {config.MAX_PAYMENT_CARDS} payment cards. "
                    "Remove one to add another."
                ),
                "code": "CARD_LIMIT",
            }, 400)
        if errors:
            return _errors_result(errors)
        CardRepository.add(conn, user.id, card, encrypt_card_number(card["number"]))
    _notify(user, [f"{card['brand']} card ending in {card['number'][-4:]} added"])
    return ServiceResult({
        "message": f"Your {card['brand']} card ending in {card['number'][-4:]} has been saved."
    }, 201)


def delete_card(user, card_id):
    with db_transaction() as conn:
        card = next((item for item in CardRepository.list(conn, user.id) if item["id"] == card_id), None)
        removed = card is not None and CardRepository.delete(conn, user.id, card_id)
    if not removed:
        return ServiceResult({"error": "That card wasn't found on your account."}, 404)
    _notify(user, [f"{card['brand']} card ending in {card['lastFour']} removed"])
    return ServiceResult({"message": "The card has been removed."})


def list_favorites(user):
    conn = get_db_connection()
    try:
        movies = FavoriteRepository.list_movies(conn, user.id)
    finally:
        conn.close()
    return ServiceResult(movies)


def add_favorite(user, movie_id):
    if not isinstance(movie_id, int):
        return ServiceResult({"error": "A valid movie is required."}, 400)
    with db_transaction() as conn:
        movie = MovieRepository.find(conn, movie_id)
        if movie is None:
            return ServiceResult({"error": "That movie wasn't found."}, 404)
        FavoriteRepository.add_movie(conn, user.id, movie_id)
    return ServiceResult({"message": f"{movie['title']} was added to your favorites."}, 201)


def remove_favorite(user, movie_id):
    with db_transaction() as conn:
        movie = MovieRepository.find(conn, movie_id)
        FavoriteRepository.remove_movie(conn, user.id, movie_id)
    title = movie["title"] if movie else "The movie"
    return ServiceResult({"message": f"{title} was removed from your favorites."})


def get_genre_preferences(user):
    conn = get_db_connection()
    try:
        selected = FavoriteRepository.list_genres(conn, user.id)
        available = MovieRepository.genres(conn)
    finally:
        conn.close()
    return ServiceResult({"genres": selected, "available": available})


def save_genre_preferences(user, genres):
    if not isinstance(genres, list):
        return ServiceResult({"error": "Genres must be a list."}, 400)
    with db_transaction() as conn:
        available = set(MovieRepository.genres(conn))
        unknown = [genre for genre in genres if genre not in available]
        if unknown:
            return ServiceResult({"error": f"Unknown genre: {unknown[0]}"}, 400)
        FavoriteRepository.replace_genres(conn, user.id, sorted(set(genres)))
    return ServiceResult({"message": "Your movie preferences have been saved."})
