"""Application composition root: configure Flask and register presentation routes.

Layers:
    frontend/             browser presentation (HTML/CSS/JS)
    backend/presentation/       HTTP controllers and response presenters
    backend/application/        application use cases and business rules
    backend/data_access/         repositories and database connections
    backend/infrastructure/      configuration and external integrations
"""
import os
from datetime import timedelta
from urllib.parse import quote

from flask import Flask, redirect, request, send_from_directory

from backend.infrastructure import config
from backend.infrastructure.email_service import EmailService
from backend.infrastructure.security import current_user
from backend.presentation.routes.admin import admin_bp
from backend.presentation.routes.auth import auth_bp
from backend.presentation.routes.movies import movies_bp
from backend.presentation.routes.profile import profile_bp

app = Flask(__name__, static_folder=str(config.FRONTEND_DIR), static_url_path="")
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,      # JavaScript can't read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",     # other sites can't send requests with it
    PERMANENT_SESSION_LIFETIME=timedelta(days=config.REMEMBER_ME_DAYS),
)

app.register_blueprint(movies_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(admin_bp)

# Pages that need a login, and which role may open them (lowercase, since Windows file names aren't case-sensitive).
PROTECTED_PAGES = {
    "/pages/profile/profile_page.html": "CUSTOMER",
    "/pages/profile/address_info_page.html": "CUSTOMER",
    "/pages/profile/payment_info_page.html": "CUSTOMER",
    "/pages/admin/admin_page.html": "ADMIN",
}
# Pages a logged-in user doesn't need, so they're sent to their home page instead.
LOGGED_OUT_ONLY_PAGES = {"/pages/auth/login_page.html", "/pages/auth/signup_page.html"}


def _home_for(user):
    if user.role == "ADMIN":
        return "/pages/admin/Admin_Page.html"
    return "/pages/public/Home_Page.html"


@app.before_request
def enforce_page_access():
    path = request.path.lower()
    if path in PROTECTED_PAGES:
        user = current_user()
        if user is None:
            login_url = f"/pages/auth/Login_Page.html?next={quote(request.full_path.rstrip('?'))}"
            return redirect(login_url)
        if user.role != PROTECTED_PAGES[path]:
            return redirect("/pages/errors/Access_Denied.html")
    elif path in LOGGED_OUT_ONLY_PAGES:
        user = current_user()
        if user is not None:
            return redirect(_home_for(user))


@app.after_request
def no_cache_for_private_data(response):
    """Stop the browser from showing a cached profile/admin page after logout (Back button)."""
    if request.path.startswith("/api/") or request.path.lower() in PROTECTED_PAGES:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def home():
    return send_from_directory(config.FRONTEND_DIR / "pages" / "public", "Home_Page.html")


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # the reloader starts this file twice; check once
        EmailService.check_connection()
    app.run(debug=True)
