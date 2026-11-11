"""Use cases for the administration dashboard."""
from backend.application.services.results import ServiceResult
from backend.data_access.db import get_db_connection
from backend.data_access.repositories import AdminRepository


def get_summary(admin):
    conn = get_db_connection()
    try:
        summary = AdminRepository.summary(conn)
    finally:
        conn.close()
    return ServiceResult({"adminName": admin.first_name, **summary})
