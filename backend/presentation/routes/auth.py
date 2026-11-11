"""HTTP endpoints for account registration and authentication."""
from flask import Blueprint, jsonify, redirect, request, session

from backend.application.services import auth as auth_service
from backend.infrastructure.security import current_user
from backend.presentation.presenters import service_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

CUSTOMER_HOME = "/Home_Page.html"
ADMIN_HOME = "/Admin_Home.html"


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _safe_next(next_path, role):
    """Only allow redirects to pages on this site after login."""
    if role == "ADMIN":
        return ADMIN_HOME
    if (
        isinstance(next_path, str)
        and next_path.startswith("/")
        and not next_path.startswith("//")
        and "\\" not in next_path
        and not next_path.lower().startswith(ADMIN_HOME.lower())
    ):
        return next_path
    return CUSTOMER_HOME


@auth_bp.post("/register")
def register():
    result = auth_service.register(_json_body(), request.host_url)
    return service_response(result)


@auth_bp.get("/verify")
def verify_email():
    result = auth_service.verify_email(request.args.get("token", ""))
    target = "/Login_Page.html?verified=1" if result.data["verified"] else "/Login_Page.html?verified=invalid"
    return redirect(target)


@auth_bp.post("/resend-verification")
def resend_verification():
    result = auth_service.resend_verification(
        _json_body().get("email"), request.host_url
    )
    return service_response(result)


@auth_bp.post("/login")
def login():
    data = _json_body()
    result = auth_service.login(
        data.get("identifier"), data.get("password"), data.get("remember")
    )
    if result.status != 200:
        return service_response(result)

    user = result.data["user"]
    session.clear()
    session["user_id"] = user.id
    session.permanent = result.data["remember"]
    return jsonify({
        "message": f"Welcome back, {user.first_name}!",
        "user": user.to_public_dict(),
        "redirect": _safe_next(data.get("next"), user.role),
    })


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "You have been logged out."})


@auth_bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return jsonify({"loggedIn": False, "user": None})
    return jsonify({"loggedIn": True, "user": user.to_public_dict()})


@auth_bp.post("/forgot-password")
def forgot_password():
    result = auth_service.forgot_password(
        _json_body().get("email"), request.host_url
    )
    return service_response(result)


@auth_bp.get("/reset-password/check")
def check_reset_token():
    result = auth_service.check_reset_token(request.args.get("token", ""))
    return service_response(result)


@auth_bp.post("/reset-password")
def reset_password():
    result = auth_service.reset_password(_json_body())
    if result.status == 200:
        session.clear()
    return service_response(result)
