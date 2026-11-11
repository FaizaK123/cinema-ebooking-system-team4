"""Compatibility entry point for the Flask application."""
import os

from backend.presentation.app import app
from backend.infrastructure.email_service import EmailService


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        EmailService.check_connection()
    app.run(debug=True)
