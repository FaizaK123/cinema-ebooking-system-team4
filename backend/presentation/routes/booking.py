"""HTTP endpoints for the customer booking flow: showtime -> tickets -> seats -> checkout."""
from flask import Blueprint, request

from backend.application.services import booking as booking_service
from backend.infrastructure.security import current_user, login_required
from backend.presentation.presenters import service_response

booking_bp = Blueprint("booking", __name__)


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# ---- Open to everyone (seats can be chosen without logging in) ----

@booking_bp.get("/api/ticket-types")
def ticket_types():
    return service_response(booking_service.list_ticket_types())


@booking_bp.get("/api/shows/<int:show_id>")
def get_show(show_id):
    return service_response(booking_service.get_show(show_id))


@booking_bp.get("/api/shows/<int:show_id>/seats")
def get_seat_map(show_id):
    return service_response(booking_service.get_seat_map(show_id))


@booking_bp.post("/api/booking/start")
def start_booking():
    return service_response(booking_service.start_booking(_json_body()))


@booking_bp.post("/api/booking/seats")
def select_seats():
    return service_response(booking_service.select_seats(_json_body()))


@booking_bp.get("/api/booking/current")
def get_selection():
    return service_response(booking_service.get_selection())


@booking_bp.delete("/api/booking/current")
def cancel_selection():
    return service_response(booking_service.cancel_selection())


# ---- Checkout needs a logged-in customer (anyone else gets 401 and is sent to log in) ----

@booking_bp.get("/api/booking/order-summary")
@login_required(role="CUSTOMER")
def order_summary():
    return service_response(booking_service.get_order_summary(current_user()))


@booking_bp.post("/api/booking/email")
@login_required(role="CUSTOMER")
def confirm_email():
    return service_response(booking_service.confirm_email(current_user(), _json_body()))


@booking_bp.get("/api/booking/payment")
@login_required(role="CUSTOMER")
def payment_page():
    return service_response(booking_service.get_payment_page(current_user()))
