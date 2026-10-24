"""App configuration: file paths, secret keys, and email (SMTP) settings.

Settings come from environment variables. For local development, put them in
backend/.env (copy backend/.env.example). That file is git-ignored so passwords
never reach GitHub.
"""
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = (BASE_DIR / ".." / "frontend").resolve()
INSTANCE_DIR = BASE_DIR / "instance"  # machine-specific files (keys, dev outbox), git-ignored


def _load_env_file(path):
    """Read KEY=VALUE lines from a .env file without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_or_create_secret(env_name, file_name, generate):
    """Use the environment variable if set, otherwise a key file in instance/ (created on first run)."""
    if os.environ.get(env_name):
        return os.environ[env_name]
    key_path = INSTANCE_DIR / file_name
    if not key_path.exists():
        INSTANCE_DIR.mkdir(exist_ok=True)
        key_path.write_text(generate(), encoding="utf-8")
    return key_path.read_text(encoding="utf-8").strip()


_load_env_file(BASE_DIR / ".env")

DB_PATH = Path(os.environ.get("CES_DB_PATH", BASE_DIR / "movies.db"))

# Signs the session cookie. Anyone with this key could forge a login, so it is never committed.
SECRET_KEY = _read_or_create_secret("SECRET_KEY", "secret.key", lambda: secrets.token_hex(32))

# Encrypts payment card numbers. If this key is lost, stored card numbers can't be decrypted.
CARD_ENCRYPTION_KEY = _read_or_create_secret(
    "CARD_ENCRYPTION_KEY", "card.key", lambda: Fernet.generate_key().decode()
)

# Email. If SMTP_HOST is empty, emails are written to instance/outbox/ instead of being sent.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USERNAME or "no-reply@ces.local")
OUTBOX_DIR = INSTANCE_DIR / "outbox"

# Default admin account created by init_db.py (change these in .env before a real demo).
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@ces.local")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin1234!")

VERIFY_TOKEN_HOURS = 24
RESET_TOKEN_MINUTES = 30
REMEMBER_ME_DAYS = 30
MAX_PAYMENT_CARDS = 3
