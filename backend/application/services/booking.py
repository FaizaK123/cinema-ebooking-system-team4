"""Booking use cases: showtime details, seat map, ticket + seat selection, order summary, payment page.

Flow:  Movie -> Showtime -> start_booking (ticket counts) -> seat map -> select_seats -> checkout
       (login required) -> order summary -> confirm_email -> payment page (mockup).

Anyone can pick seats without an account. The picked seats are *held* (show_seats.status = 'HELD')
for the browser session that picked them, and show as unavailable to everybody else. A hold lasts
config.SEAT_HOLD_MINUTES and every checkout step renews it; an abandoned hold frees itself. Nothing
becomes BOOKED in this sprint because payment and final confirmation come later.
"""
import re
from datetime import datetime

from backend.application.services.results import ServiceResult
from backend.data_access.db import db_transaction, get_db_connection
from backend.data_access.repositories import (
    CardRepository,
    MovieRepository,
    SeatRepository,
    ShowRepository,
    TicketTypeRepository,
)
from backend.infrastructure import booking_session, config
from backend.infrastructure.timeutil import local_now, utc_iso_in, utc_now_iso
from backend.infrastructure.validators import (
    TICKET_CATEGORIES,
    whole_number,
    validate_email,
    validate_ticket_counts,
)

TICKET_LABELS = {"ADULT": "Adult", "CHILD": "Child", "SENIOR": "Senior"}


class _SeatsTaken(Exception):
    """Raised inside a transaction so that it rolls back when a chosen seat is no longer free."""


def _error(message, status=400, **extra):
    return ServiceResult({"error": message, **extra}, status)


def _errors_result(errors, status=400):
    return ServiceResult({"error": "Please fix the highlighted fields.", "errors": errors}, status)


def _is_upcoming(show):
    start = datetime.strptime(f"{show['date']} {show['time']}", "%Y-%m-%d %H:%M")
    return start > local_now()


def _seat_sort_key(label):
    match = re.fullmatch(r"([A-Z]+)(\d+)", label)
    return (match.group(1), int(match.group(2))) if match else (label, 0)


def _money(cents):
    return round(cents / 100, 2)


def _price_cents(ticket_types, category):
    return round(ticket_types[category]["price"] * 100)


def _movie_dict(movie):
    return {
        "id": movie["id"],
        "title": movie["title"],
        "poster": movie["poster"],
        "rating": movie["rating"],
        "runtime": movie["runtime"],
    }


def _ticket_types_list(ticket_types):
    return [
        {"type": category, "label": TICKET_LABELS[category], "price": _money(_price_cents(ticket_types, category))}
        for category in TICKET_CATEGORIES
    ]


# ---------------------------------------------------------------- Showtime and seat map (no login needed)

def get_show(show_id):
    conn = get_db_connection()
    try:
        show = ShowRepository.find(conn, show_id)
        if show is None:
            return _error("That showtime wasn't found.", 404)
        movie = MovieRepository.find(conn, show["movieId"])
        ticket_types = TicketTypeRepository.all(conn)
        seats = SeatRepository.seat_map(conn, show_id, booking_session.hold_token(), utc_now_iso())
    finally:
        conn.close()
    return ServiceResult({
        "show": show,
        "movie": _movie_dict(movie),
        "ticketTypes": _ticket_types_list(ticket_types),
        "capacity": len(seats),
        "availableSeats": sum(1 for seat in seats if seat["status"] in ("AVAILABLE", "SELECTED")),
        "bookable": _is_upcoming(show),
    })


def get_seat_map(show_id):
    """Every seat of the showtime's showroom with its status:
    AVAILABLE, BOOKED (taken), HELD (picked by someone else, not yet paid) or SELECTED (picked by this visitor)."""
    conn = get_db_connection()
    try:
        show = ShowRepository.find(conn, show_id)
        if show is None:
            return _error("That showtime wasn't found.", 404)
        seats = SeatRepository.seat_map(conn, show_id, booking_session.hold_token(), utc_now_iso())
    finally:
        conn.close()
    counts = {status: sum(1 for seat in seats if seat["status"] == status)
              for status in ("AVAILABLE", "SELECTED", "HELD", "BOOKED")}
    return ServiceResult({
        "show": show,
        "rows": sorted({seat["row"] for seat in seats}),
        "seatsPerRow": max((seat["number"] for seat in seats), default=0),
        "seats": seats,
        "counts": counts,
        "bookable": _is_upcoming(show),
    })


def list_ticket_types():
    conn = get_db_connection()
    try:
        ticket_types = TicketTypeRepository.all(conn)
    finally:
        conn.close()
    return ServiceResult(_ticket_types_list(ticket_types))


# ---------------------------------------------------------------- Selection summary shared by every step

def _selection_summary(conn, draft):
    show = ShowRepository.find(conn, draft["showId"])
    movie = MovieRepository.find(conn, show["movieId"])
    ticket_types = TicketTypeRepository.all(conn)
    labels = SeatRepository.labels(conn, draft["showId"], draft["seatIds"])
    seats = sorted(
        ({"seatId": seat_id, "label": label} for seat_id, label in labels.items()),
        key=lambda seat: _seat_sort_key(seat["label"]),
    )
    tickets = []
    total_cents = 0
    for category in TICKET_CATEGORIES:
        quantity = draft["tickets"].get(category, 0)
        if quantity:
            unit_cents = _price_cents(ticket_types, category)
            total_cents += unit_cents * quantity
            tickets.append({
                "type": category,
                "label": TICKET_LABELS[category],
                "quantity": quantity,
                "pricePerTicket": _money(unit_cents),
                "lineTotal": _money(unit_cents * quantity),
            })
    return {
        "movie": _movie_dict(movie),
        "show": show,
        "seats": seats,
        "tickets": tickets,
        "ticketCount": sum(draft["tickets"].values()),
        "totalBeforeTax": _money(total_cents),
    }


# ---------------------------------------------------------------- Start booking and seat selection (no login needed)

def _resolve_request(data):
    """The showId and ticket counts for a request: from the body if given, else from the booking in progress."""
    draft = booking_session.get_booking()
    errors = {}
    raw_show_id = data.get("showId", draft["showId"] if draft else None)
    show_id = whole_number(raw_show_id)
    if raw_show_id in (None, ""):
        errors["showId"] = "Select a showtime first."
    elif show_id is None:
        errors["showId"] = "Select a valid showtime."

    tickets = None
    if "tickets" in data:
        tickets, ticket_errors = validate_ticket_counts(data.get("tickets"))
        errors.update(ticket_errors)
    elif draft:
        tickets = dict(draft["tickets"])
    else:
        errors["tickets"] = "Choose your tickets first."
    return show_id, tickets, errors


def _check_bookable(conn, show_id, tickets):
    """Returns an error ServiceResult, or None if this showtime can be booked with these ticket counts."""
    show = ShowRepository.find(conn, show_id)
    if show is None:
        return _error("That showtime wasn't found.", 404)
    if not _is_upcoming(show):
        return _error("This showtime has already started. Please choose another one.", 409)
    seats = SeatRepository.seat_map(conn, show_id, booking_session.hold_token(), utc_now_iso())
    free = sum(1 for seat in seats if seat["status"] in ("AVAILABLE", "SELECTED"))  # SELECTED = this visitor's own
    if sum(tickets.values()) > free:
        message = f"Only {free} seat(s) are left for this showtime." if free else "This showtime is sold out."
        return _error(message, 409, errors={"tickets": message})
    return None


def start_booking(data):
    """Step 1: the visitor picked a showtime and entered how many tickets of each age category."""
    data = data if isinstance(data, dict) else {}
    show_id, tickets, errors = _resolve_request(data)
    if errors:
        return _errors_result(errors)

    conn = get_db_connection()
    try:
        problem = _check_bookable(conn, show_id, tickets)
        if problem:
            return problem
    finally:
        conn.close()

    token = booking_session.hold_token(create=True)
    with db_transaction() as conn:
        SeatRepository.release_for_token(conn, token)  # new ticket counts: start the seat choice over
    booking_session.set_booking({"showId": show_id, "tickets": tickets, "seatIds": [], "email": None})

    conn = get_db_connection()
    try:
        ticket_types = TicketTypeRepository.all(conn)
        show = ShowRepository.find(conn, show_id)
        movie = MovieRepository.find(conn, show["movieId"])
    finally:
        conn.close()
    total_cents = sum(_price_cents(ticket_types, category) * count for category, count in tickets.items())
    return ServiceResult({
        "message": "Tickets saved. Now choose your seats.",
        "movie": _movie_dict(movie),
        "show": show,
        "tickets": tickets,
        "ticketCount": sum(tickets.values()),
        "totalBeforeTax": _money(total_cents),
    })


def select_seats(data):
    """Step 2: reserve the chosen seats. The number of seats must equal the number of tickets."""
    data = data if isinstance(data, dict) else {}
    show_id, tickets, errors = _resolve_request(data)
    if errors:
        return _errors_result(errors)
    total = sum(tickets.values())

    raw_seats = data.get("seatIds")
    seat_ids = []
    if not isinstance(raw_seats, list):
        errors["seats"] = f"Select {total} seat(s)."
    else:
        for raw in raw_seats:
            seat_id = whole_number(raw)
            if seat_id is None:
                errors["seats"] = "One of the selected seats isn't valid."
                break
            seat_ids.append(seat_id)
        if "seats" not in errors and len(set(seat_ids)) != len(seat_ids):
            errors["seats"] = "The same seat was selected more than once."
        if "seats" not in errors and len(seat_ids) != total:
            noun = "seat" if total == 1 else "seats"
            errors["seats"] = f"You chose {total} ticket(s), so select exactly {total} {noun} (you selected {len(seat_ids)})."
    if errors:
        return _errors_result(errors)

    conn = get_db_connection()
    try:
        problem = _check_bookable(conn, show_id, tickets)
        if problem:
            return problem
        known = SeatRepository.labels(conn, show_id, seat_ids)
    finally:
        conn.close()
    if len(known) != len(seat_ids):
        return _errors_result({"seats": "One of the selected seats isn't in this showroom."})

    token = booking_session.hold_token(create=True)
    try:
        with db_transaction() as conn:
            conn.execute("BEGIN IMMEDIATE")  # nobody else can grab these seats between our check and our update
            SeatRepository.release_for_token(conn, token)  # replaces this visitor's earlier selection
            if not SeatRepository.hold(conn, show_id, seat_ids, token, utc_iso_in(config.SEAT_HOLD_MINUTES), utc_now_iso()):
                raise _SeatsTaken()
    except _SeatsTaken:
        conn = get_db_connection()
        try:
            status = {seat["seatId"]: seat for seat in SeatRepository.seat_map(conn, show_id, token, utc_now_iso())}
        finally:
            conn.close()
        taken = sorted(
            (status[i]["label"] for i in seat_ids if status[i]["status"] in ("BOOKED", "HELD")),
            key=_seat_sort_key,
        )
        names = ", ".join(taken) if taken else "one of those seats"
        message = f"Seat {names} is no longer available. Please choose different seats."
        if len(taken) > 1:
            message = f"Seats {names} are no longer available. Please choose different seats."
        return _error(message, 409, errors={"seats": message}, unavailableSeats=taken)

    draft = {"showId": show_id, "tickets": tickets, "seatIds": sorted(seat_ids), "email": None}
    booking_session.set_booking(draft)
    conn = get_db_connection()
    try:
        summary = _selection_summary(conn, draft)
    finally:
        conn.close()
    return ServiceResult({
        "message": "Your seats are reserved. Continue to checkout.",
        "holdMinutes": config.SEAT_HOLD_MINUTES,
        **summary,
    })


def get_selection():
    """The booking in progress (so a page can be rebuilt after a refresh or a login), or null."""
    draft = booking_session.get_booking()
    if draft is None:
        return ServiceResult({"selection": None})
    conn = get_db_connection()
    try:
        show = ShowRepository.find(conn, draft["showId"])
        if show is None or not _is_upcoming(show):
            booking_session.clear_booking()
            return ServiceResult({"selection": None, "expired": True, "message": "That showtime is no longer available."})
        if draft["seatIds"] and not SeatRepository.still_held(
            conn, draft["showId"], draft["seatIds"], booking_session.hold_token(), utc_now_iso()
        ):
            booking_session.clear_booking()
            return ServiceResult({
                "selection": None, "expired": True,
                "message": "Your seat reservation expired. Please select your seats again.",
            })
        summary = _selection_summary(conn, draft)
    finally:
        conn.close()
    return ServiceResult({"selection": {"seatsReserved": bool(draft["seatIds"]), **summary}})


def release_holds():
    """Free this visitor's reserved seats and forget the booking in progress."""
    token = booking_session.hold_token()
    if token:
        with db_transaction() as conn:
            SeatRepository.release_for_token(conn, token)
    booking_session.clear_booking()


def cancel_selection():
    release_holds()
    return ServiceResult({"message": "Your seat selection was cancelled."})


# ---------------------------------------------------------------- Checkout (login required)

def _checkout_draft(conn):
    """The booking in progress, checked and renewed for checkout. Returns (draft, None) or (None, error result)."""
    draft = booking_session.get_booking()
    if draft is None or not draft["seatIds"]:
        return None, _error("You haven't selected any seats yet. Choose a showtime and seats first.", 409, noSelection=True)
    show = ShowRepository.find(conn, draft["showId"])
    if show is None or not _is_upcoming(show):
        booking_session.clear_booking()
        return None, _error("This showtime is no longer available. Please choose another one.", 409, expired=True)
    token = booking_session.hold_token()
    now = utc_now_iso()
    if not token or not SeatRepository.still_held(conn, draft["showId"], draft["seatIds"], token, now):
        booking_session.clear_booking()
        return None, _error("Your seat reservation expired. Please select your seats again.", 409, expired=True)
    SeatRepository.renew(conn, draft["showId"], token, utc_iso_in(config.SEAT_HOLD_MINUTES), now)
    return draft, None


def get_order_summary(user):
    """'Proceed to Checkout': the order summary, with the email the confirmation will go to."""
    with db_transaction() as conn:
        draft, problem = _checkout_draft(conn)
        if problem:
            return problem
        summary = _selection_summary(conn, draft)
    return ServiceResult({
        **summary,
        "accountEmail": user.email,
        "email": draft["email"] or user.email,
        "emailConfirmed": bool(draft["email"]),
    })


def confirm_email(user, data):
    """The customer confirms their account email or types a different one for this order."""
    data = data if isinstance(data, dict) else {}
    raw = data.get("email")
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        email = user.email
    else:
        email, error = validate_email(raw)
        if error:
            return _errors_result({"email": error})

    with db_transaction() as conn:
        draft, problem = _checkout_draft(conn)
        if problem:
            return problem
    draft = {**draft, "email": email}
    booking_session.set_booking(draft)
    return ServiceResult({
        "message": f"Your order confirmation will be sent to {email}.",
        "email": email,
        "usingAccountEmail": email == user.email,
    })


def get_payment_page(user):
    """Data for the payment page. It's a mockup this sprint: it shows the order but takes no payment."""
    with db_transaction() as conn:
        draft, problem = _checkout_draft(conn)
        if problem:
            return problem
        if not draft["email"]:
            return _error("Please confirm the email address for your order first.", 409, needsEmail=True)
        summary = _selection_summary(conn, draft)
        cards = CardRepository.list(conn, user.id)
    return ServiceResult({
        "order": summary,
        "email": draft["email"],
        "savedCards": cards,
        "paymentProcessing": False,
        "message": "Payment processing isn't available yet. This page previews the payment step.",
    })
