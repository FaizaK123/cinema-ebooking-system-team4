"""The visitor's in-progress booking, kept in the signed session cookie.

People choose seats before they log in, so the booking can't belong to a user account yet.
Instead the browser session carries:
    hold_token  random id written onto the seats it reserves (show_seats.held_by)
    booking     {"showId", "tickets": {"ADULT": n, ...}, "seatIds": [...], "email": str or None}
Logging in keeps both (see the login route), so the seats stay reserved through the login step.
"""
import secrets

from flask import session


def hold_token(create=False):
    token = session.get("hold_token")
    if token is None and create:
        token = secrets.token_urlsafe(16)
        session["hold_token"] = token
    return token


def get_booking():
    booking = session.get("booking")
    return booking if isinstance(booking, dict) else None


def set_booking(booking):
    session["booking"] = booking


def clear_booking():
    session.pop("booking", None)


def preserved_values():
    """The booking-related session values that must survive a login."""
    return {key: session[key] for key in ("hold_token", "booking") if key in session}
