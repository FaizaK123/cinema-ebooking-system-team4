"""Password hashing, card encryption, one-time tokens, and route access control."""
import hashlib
import secrets
from functools import wraps

from cryptography.fernet import Fernet
from flask import g, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash

from config import CARD_ENCRYPTION_KEY
from db import get_db_connection
from repositories import UserRepository

_fernet = Fernet(CARD_ENCRYPTION_KEY.encode())


# ---- Passwords: one-way salted hash (scrypt), never stored or logged in plain text ----

def hash_password(password):
    return generate_password_hash(password)


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


# ---- Payment cards: reversible encryption so the number can be used at checkout later ----

def encrypt_card_number(card_number):
    return _fernet.encrypt(card_number.encode()).decode()


def decrypt_card_number(encrypted):
    return _fernet.decrypt(encrypted.encode()).decode()


# ---- One-time tokens (email verification, password reset) ----

def new_token():
    """Random token for an emailed link. Only its hash is stored in the database."""
    return secrets.token_urlsafe(32)


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


# ---- Sessions and access control ----

def current_user():
    """The logged-in user (loaded fresh from the database), or None.

    Loading from the database on each request means a suspended or deleted
    account loses access immediately, not only when the cookie expires.
    """
    if "current_user" in g:
        return g.current_user
    user = None
    user_id = session.get("user_id")
    if user_id is not None:
        conn = get_db_connection()
        try:
            user = UserRepository.find_by_id(conn, user_id)
        finally:
            conn.close()
        if user is None or (user.role == "CUSTOMER" and user.status != "ACTIVE"):
            session.clear()
            user = None
    g.current_user = user
    return user


def login_required(role=None):
    """Decorator for API routes: 401 if not logged in, 403 if the role doesn't match."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify({"error": "Please log in to continue."}), 401
            if role and user.role != role:
                return jsonify({"error": "You don't have permission to do that."}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
