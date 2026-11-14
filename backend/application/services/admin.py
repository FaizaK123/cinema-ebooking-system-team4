"""Use cases for the administration portal: dashboard, movies, showtimes and promotions."""
import re
import secrets
import sqlite3

from backend.application.services.results import ServiceResult
from backend.data_access.db import db_transaction, get_db_connection
from backend.data_access.repositories import (
    AdminRepository,
    MovieRepository,
    PromotionRepository,
    ShowRepository,
    ShowroomRepository,
)
from backend.infrastructure import config
from backend.infrastructure.email_service import EmailService
from backend.infrastructure.timeutil import local_now, runtime_label, time_label
from backend.infrastructure.validators import (
    parse_hhmm,
    parse_iso_date,
    validate_movie,
    validate_poster,
    validate_promotion,
    validate_showtime,
)


def _errors_result(errors, status=400):
    return ServiceResult({"error": "Please fix the highlighted fields.", "errors": errors}, status)


def get_summary(admin):
    conn = get_db_connection()
    try:
        summary = AdminRepository.summary(conn)
    finally:
        conn.close()
    return ServiceResult({"adminName": admin.first_name, **summary})


# ---------------------------------------------------------------- Movies

def _poster_file_name(title, extension):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "movie"
    return f"{slug}-{secrets.token_hex(4)}{extension}"


def add_movie(data, poster_file):
    """Validate the Add Movie form, save the poster image, then store the movie."""
    movie, errors = validate_movie(data)
    image, extension, poster_error = validate_poster(poster_file, config.MAX_POSTER_BYTES)
    if poster_error:
        errors["poster"] = poster_error
    if errors:
        return _errors_result(errors)

    config.POSTER_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_name = _poster_file_name(movie["title"], extension)
    poster_path = config.POSTER_UPLOAD_DIR / file_name
    poster_path.write_bytes(image)

    movie["runtime"] = runtime_label(movie["duration"])
    movie["poster"] = f"/images/uploads/{file_name}"
    try:
        with db_transaction() as conn:
            conn.execute("BEGIN IMMEDIATE")  # lock now so two admins can't add the same title at once
            if MovieRepository.title_exists(conn, movie["title"]):
                poster_path.unlink(missing_ok=True)
                return _errors_result({"title": "A movie with this title already exists."}, 409)
            movie_id = MovieRepository.create(conn, movie)
    except Exception:
        poster_path.unlink(missing_ok=True)
        raise

    return ServiceResult({
        "message": f"{movie['title']} was added.",
        "movie": {
            "id": movie_id,
            "title": movie["title"],
            "genre": movie["genre"],
            "rating": movie["rating"],
            "runtime": movie["runtime"],
            "releaseDate": movie["releaseDate"],
            "description": movie["description"],
            "poster": movie["poster"],
            "trailer": movie["trailer"],
            "isCurrent": movie["status"] == "CURRENTLY_RUNNING",
        },
    }, 201)


# ---------------------------------------------------------------- Showrooms and showtimes

def _rooms_with_availability(conn, show_date, show_time):
    rooms = ShowroomRepository.list_all(conn)
    if show_date and show_time:
        busy = ShowroomRepository.busy_room_ids(conn, show_date, show_time)
        for room in rooms:
            room["available"] = room["id"] not in busy
    return rooms


def list_showrooms(date_text, time_text):
    """All showrooms. With a date AND time, each one says whether it is free at that moment."""
    show_date = show_time = None
    if date_text or time_text:
        errors = {}
        show_date = parse_iso_date((date_text or "").strip())
        show_time = parse_hhmm((time_text or "").strip())
        if show_date is None:
            errors["date"] = "Enter a valid date (YYYY-MM-DD) to check availability."
        if show_time is None:
            errors["time"] = "Enter a valid time (HH:MM) to check availability."
        if errors:
            return _errors_result(errors)
        show_date = show_date.isoformat()
    conn = get_db_connection()
    try:
        rooms = _rooms_with_availability(conn, show_date, show_time)
    finally:
        conn.close()
    return ServiceResult(rooms)


def list_showtimes(movie_id):
    conn = get_db_connection()
    try:
        showtimes = ShowRepository.list_all(conn, movie_id)
    finally:
        conn.close()
    return ServiceResult(showtimes)


def add_showtime(data):
    """Schedule a movie in a showroom at a date and time. One showroom can't show two movies at the same time."""
    showtime, errors = validate_showtime(data, local_now())
    if errors:
        return _errors_result(errors)

    def conflict(conn, existing_show_id):
        existing = ShowRepository.find(conn, existing_show_id)
        room = existing["showroom"]
        message = (
            f"{room} already has {existing['movieTitle']} at {existing['timeLabel']} on {existing['date']}. "
            "Choose another time or showroom."
        )
        body = {
            "error": message,
            "errors": {"showroomId": message},
            "showrooms": _rooms_with_availability(conn, showtime["date"], showtime["time"]),
        }
        return ServiceResult(body, 409)

    with db_transaction() as conn:
        conn.execute("BEGIN IMMEDIATE")  # check-then-insert must not interleave with another admin's request
        if MovieRepository.find(conn, showtime["movieId"]) is None:
            return _errors_result({"movieId": "That movie doesn't exist."}, 404)
        if ShowroomRepository.find(conn, showtime["showroomId"]) is None:
            return _errors_result({"showroomId": "That showroom doesn't exist."}, 404)
        clash = ShowRepository.find_in_room_at(conn, showtime["showroomId"], showtime["date"], showtime["time"])
        if clash:
            return conflict(conn, clash["show_id"])
        try:
            show_id = ShowRepository.create(
                conn, showtime["movieId"], showtime["showroomId"], showtime["date"], showtime["time"]
            )
        except sqlite3.IntegrityError:  # the database's own UNIQUE rule is the last line of defense
            clash = ShowRepository.find_in_room_at(conn, showtime["showroomId"], showtime["date"], showtime["time"])
            if clash:
                return conflict(conn, clash["show_id"])
            raise
        created = ShowRepository.find(conn, show_id)

    return ServiceResult({
        "message": (
            f"{created['movieTitle']} is scheduled in {created['showroom']} "
            f"on {created['date']} at {time_label(created['time'])}."
        ),
        "showtime": created,
    }, 201)


# ---------------------------------------------------------------- Promotions

def list_promotions():
    conn = get_db_connection()
    try:
        promotions = PromotionRepository.list_all(conn)
    finally:
        conn.close()
    return ServiceResult(promotions)


def add_promotion(data):
    """Save a promotion, then email it to subscribed customers only (unless sendEmail is false)."""
    data = data if isinstance(data, dict) else {}
    promotion, errors = validate_promotion(data)
    send_email = data.get("sendEmail", True)
    if not isinstance(send_email, bool):
        errors["sendEmail"] = "sendEmail must be true or false."
    if errors:
        return _errors_result(errors)

    try:
        with db_transaction() as conn:
            if PromotionRepository.exists(conn, promotion["promoCode"]):
                return _errors_result({"promoCode": "A promotion with this code already exists."}, 409)
            PromotionRepository.create(conn, promotion)
            recipients = PromotionRepository.subscribers(conn) if send_email else []
    except sqlite3.IntegrityError:
        return _errors_result({"promoCode": "A promotion with this code already exists."}, 409)

    sent = sum(1 for person in recipients if EmailService.send_promotion(person["firstName"], person["email"], promotion))
    failed = len(recipients) - sent
    if not send_email:
        note = "Promotion saved. No emails were sent."
    elif not recipients:
        note = "Promotion saved. No subscribed customers to email."
    elif failed:
        note = f"Promotion saved. Emailed {sent} subscribed customer(s); {failed} email(s) could not be sent."
    else:
        note = f"Promotion saved and emailed to {sent} subscribed customer(s)."
    return ServiceResult({
        "message": note,
        "promotion": {key: promotion[key] for key in ("promoCode", "description", "discountPercent", "startDate", "endDate")},
        "email": {"subscribers": len(recipients), "sent": sent, "failed": failed},
    }, 201)
