"""Flask entry point: serves the frontend pages and registers the API routes.

Layers:
    frontend/            presentation (HTML/CSS/JS)
    backend/routes/      controllers: HTTP endpoints, input validation, responses
    backend/security.py, email_service.py, validators.py   services
    backend/repositories.py, db.py                         data access (all SQL)
"""
import os
from datetime import timedelta
from urllib.parse import quote

from flask import Flask, redirect, request, send_from_directory

import config
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.movies import movies_bp
from routes.profile import profile_bp
from email_service import EmailService
from security import current_user

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
    "/profile_page.html": "CUSTOMER",
    "/address_info_page.html": "CUSTOMER",
    "/payment_info_page.html": "CUSTOMER",
    "/admin_home.html": "ADMIN",
}
# Pages a logged-in user doesn't need, so they're sent to their home page instead.
LOGGED_OUT_ONLY_PAGES = {"/login_page.html", "/signup_page.html"}


def _home_for(user):
    return "/Admin_Home.html" if user.role == "ADMIN" else "/Home_Page.html"


@app.before_request
def enforce_page_access():
    path = request.path.lower()
    if path in PROTECTED_PAGES:
        user = current_user()
        if user is None:
            return redirect(f"/Login_Page.html?next={quote(request.full_path.rstrip('?'))}")
        if user.role != PROTECTED_PAGES[path]:
            return redirect("/Access_Denied.html")
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
    return send_from_directory(config.FRONTEND_DIR, "Home_Page.html")


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":  # the reloader starts this file twice; check once
        EmailService.check_connection()
    app.run(debug=True)
