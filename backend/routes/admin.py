"""Admin portal API. Sprint 2 only needs the portal home page (prototype), so this
returns the summary numbers it displays. Every route requires an ADMIN session."""
from flask import Blueprint, jsonify

from db import get_db_connection
from security import current_user, login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/summary")
@login_required(role="ADMIN")
def summary():
    conn = get_db_connection()
    try:
        movies = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        running = conn.execute("SELECT COUNT(*) FROM movies WHERE status = 'CURRENTLY_RUNNING'").fetchone()[0]
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM customers WHERE status = 'ACTIVE'").fetchone()[0]
        promotions = conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0]
    finally:
        conn.close()
    return jsonify({
        "adminName": current_user().first_name,
        "movies": movies,
        "currentlyRunning": running,
        "customers": customers,
        "activeCustomers": active,
        "promotions": promotions,
    })
