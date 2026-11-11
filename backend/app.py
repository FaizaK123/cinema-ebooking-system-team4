"""Compatibility entry point for the Flask application."""
import os

from backend.infrastructure.email_service import EmailService
from backend.presentation.app import app


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        EmailService.check_connection()
    app.run(debug=True)
