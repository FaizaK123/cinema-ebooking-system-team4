"""HTTP endpoints for the administration dashboard."""
from flask import Blueprint

from backend.application.services import admin as admin_service
from backend.infrastructure.security import current_user, login_required
from backend.presentation.presenters import service_response

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/summary")
@login_required(role="ADMIN")
def summary():
    return service_response(admin_service.get_summary(current_user()))
