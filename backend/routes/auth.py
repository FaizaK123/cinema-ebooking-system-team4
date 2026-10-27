"""Registration, email confirmation, login, logout and password reset."""
import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request, session

import config
from db import db_transaction, get_db_connection
from email_service import EmailService
from repositories import AddressRepository, CardRepository, TokenRepository, UserRepository, expiry
from security import current_user, encrypt_card_number, hash_password, hash_token, new_token, verify_password
from validators import (validate_address, validate_card, validate_email, validate_name, validate_password,
                        validate_phone)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

CUSTOMER_HOME = "/Home_Page.html"
ADMIN_HOME = "/Admin_Home.html"


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _errors_response(errors, status=400):
    return jsonify({"error": "Please fix the highlighted fields.", "errors": errors}), status


def _safe_next(next_path, role):
    """Only allow redirects to pages on this site, so a link can't send users elsewhere after login."""
    if role == "ADMIN":
        return ADMIN_HOME
    if (isinstance(next_path, str) and next_path.startswith("/") and not next_path.startswith("//")
            and "\\" not in next_path and not next_path.lower().startswith(ADMIN_HOME.lower())):
        return next_path
    return CUSTOMER_HOME


def _send_verification(conn, user_id, first_name, email):
    token = new_token()
    TokenRepository.create(conn, user_id, TokenRepository.VERIFY_EMAIL, hash_token(token),
                           expiry(hours=config.VERIFY_TOKEN_HOURS))
    link = f"{request.host_url}api/auth/verify?token={token}"
    return lambda: EmailService.send_verification(first_name, email, link)


# ---------------------------------------------------------------- Registration

@auth_bp.post("/register")
def register():
    data = _json_body()
    errors = {}

    first_name, err = validate_name(data.get("firstName"), "First name")
    if err: errors["firstName"] = err
    last_name, err = validate_name(data.get("lastName"), "Last name")
    if err: errors["lastName"] = err
    email, err = validate_email(data.get("email"))
    if err: errors["email"] = err
    phone, err = validate_phone(data.get("phone"))
    if err: errors["phone"] = err
    password, err = validate_password(data.get("password"))
    if err: errors["password"] = err
    if not data.get("confirmPassword"):
        errors["confirmPassword"] = "Please confirm your password."
    elif data.get("confirmPassword") != data.get("password"):
        errors["confirmPassword"] = "Passwords don't match."

    # Optional home address (only one allowed)
    address = None
    if data.get("address"):
        address, address_errors = validate_address(data["address"])
        errors.update({f"address.{field}": message for field, message in address_errors.items()})

    # Optional payment cards (up to 3)
    cards = []
    raw_cards = data.get("cards") or []
    if not isinstance(raw_cards, list):
        raw_cards = []
    if len(raw_cards) > config.MAX_PAYMENT_CARDS:
        errors["cards"] = f"You can save up to {config.MAX_PAYMENT_CARDS} payment cards."
    for index, raw_card in enumerate(raw_cards[:config.MAX_PAYMENT_CARDS]):
        card, card_errors = validate_card(raw_card)
        errors.update({f"cards.{index}.{field}": message for field, message in card_errors.items()})
        cards.append(card)

    conn = get_db_connection()
    try:
        if "email" not in errors and UserRepository.find_by_email(conn, email):
            errors["email"] = "An account with this email already exists. Try logging in instead."
        if "phone" not in errors and UserRepository.find_by_phone(conn, phone):
            errors["phone"] = "This phone number is already linked to another account."
    finally:
        conn.close()

    if errors:
        duplicate = errors.get("email", "").startswith("An account") or errors.get("phone", "").startswith("This phone")
        return _errors_response(errors, 409 if duplicate and set(errors) <= {"email", "phone"} else 400)

    try:
        with db_transaction() as conn:
            user_id = UserRepository.create_customer(
                conn, first_name, last_name, email, phone, hash_password(password), bool(data.get("promoOptIn"))
            )
            if address:
                AddressRepository.save(conn, user_id, address)
            for card in cards:
                CardRepository.add(conn, user_id, card, encrypt_card_number(card["number"]))
            send_email = _send_verification(conn, user_id, first_name, email)
    except sqlite3.IntegrityError as error:
        # Another request registered the same email/phone at the same moment.
        if "users.email" in str(error):
            return _errors_response({"email": "An account with this email already exists. Try logging in instead."}, 409)
        if "users.phone_num" in str(error):
            return _errors_response({"phone": "This phone number is already linked to another account."}, 409)
        raise

    email_sent = send_email()
    if email_sent:
        message = (f"Account created! We sent a confirmation email to {email}. "
                   "Click the link in it to activate your account, then log in.")
    else:
        message = ("Your account was created, but we couldn't send the confirmation email right now. "
                   "Use 'Resend confirmation email' on the login page to try again.")
    return jsonify({"message": message, "emailSent": email_sent}), 201


@auth_bp.get("/verify")
def verify_email():
    """The link in the confirmation email points here; it activates the account."""
    token = request.args.get("token", "")
    with db_transaction() as conn:
        user_id = TokenRepository.consume(conn, hash_token(token), TokenRepository.VERIFY_EMAIL) if token else None
        if user_id is None:
            return redirect("/Login_Page.html?verified=invalid")
        user = UserRepository.find_by_id(conn, user_id)
        if user and user.status == "INACTIVE":
            UserRepository.set_status(conn, user_id, "ACTIVE")
    return redirect("/Login_Page.html?verified=1")


@auth_bp.post("/resend-verification")
def resend_verification():
    email, err = validate_email(_json_body().get("email"))
    if err:
        return _errors_response({"email": err})
    send_email = None
    with db_transaction() as conn:
        user = UserRepository.find_by_email(conn, email)
        if user and user.role == "CUSTOMER" and user.status == "INACTIVE":
            send_email = _send_verification(conn, user.id, user.first_name, user.email)
    if send_email:
        send_email()
    # Same answer either way, so this can't be used to discover which emails have accounts.
    return jsonify({"message": "If that account still needs to be confirmed, we've sent a new confirmation link."})


# ---------------------------------------------------------------- Login / logout

@auth_bp.post("/login")
def login():
    data = _json_body()
    identifier = (data.get("identifier") or "").strip()
    password = data.get("password") or ""

    errors = {}
    if not identifier:
        errors["identifier"] = "Enter your email address or phone number."
    if not password:
        errors["password"] = "Enter your password."
    if errors:
        return _errors_response(errors)

    conn = get_db_connection()
    try:
        if "@" in identifier:
            user = UserRepository.find_by_email(conn, identifier.lower())
        else:
            phone, _ = validate_phone(identifier)
            user = UserRepository.find_by_phone(conn, phone) if phone else None
    finally:
        conn.close()

    # One message for "no such account" and "wrong password", so attackers can't probe for accounts.
    if user is None or not verify_password(user.password_hash, password):
        return jsonify({"error": "Incorrect email/phone number or password. Please try again."}), 401

    if user.role == "CUSTOMER" and user.status == "INACTIVE":
        return jsonify({
            "error": "Account is not verified. Please check your email to verify your account.",
            "code": "UNVERIFIED",
            "email": user.email,
        }), 403
    if user.role == "CUSTOMER" and user.status == "SUSPENDED":
        return jsonify({
            "error": "This account has been suspended. Please contact the theater for help.",
            "code": "SUSPENDED",
        }), 403

    session.clear()  # new session id at login prevents session fixation
    session["user_id"] = user.id
    session.permanent = bool(data.get("remember"))  # "Remember me": 30-day cookie, otherwise ends with the browser
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


# ---------------------------------------------------------------- Forgot / reset password

@auth_bp.post("/forgot-password")
def forgot_password():
    email, err = validate_email(_json_body().get("email"))
    if err:
        return _errors_response({"email": err})

    send_email = None
    with db_transaction() as conn:
        user = UserRepository.find_by_email(conn, email)
        if user and user.status != "SUSPENDED":
            token = new_token()
            TokenRepository.create(conn, user.id, TokenRepository.RESET_PASSWORD, hash_token(token),
                                   expiry(minutes=config.RESET_TOKEN_MINUTES))
            link = f"{request.host_url}Forgot_Password.html?token={token}"
            send_email = lambda: EmailService.send_password_reset(user.first_name, user.email, link)
    if send_email:
        send_email()
    return jsonify({
        "message": (f"If an account exists for {email}, we've sent a password reset link. "
                    f"It expires in {config.RESET_TOKEN_MINUTES} minutes.")
    })


@auth_bp.get("/reset-password/check")
def check_reset_token():
    """Lets the reset page say 'this link expired' before the user types a new password."""
    token = request.args.get("token", "")
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT expires_at, used_at FROM auth_tokens WHERE token_hash = ? AND purpose = ?",
            (hash_token(token), TokenRepository.RESET_PASSWORD),
        ).fetchone()
    finally:
        conn.close()
    valid = bool(row) and row["used_at"] is None and datetime.fromisoformat(row["expires_at"]) > datetime.now(timezone.utc)
    return jsonify({"valid": valid})


@auth_bp.post("/reset-password")
def reset_password():
    data = _json_body()
    token = data.get("token") or ""
    password, err = validate_password(data.get("password"))
    errors = {}
    if err:
        errors["password"] = err
    if data.get("confirmPassword") != data.get("password"):
        errors["confirmPassword"] = "Passwords don't match."
    if errors:
        return _errors_response(errors)

    with db_transaction() as conn:
        user_id = TokenRepository.consume(conn, hash_token(token), TokenRepository.RESET_PASSWORD) if token else None
        if user_id is None:
            return jsonify({
                "error": "This reset link is invalid or has expired. Please request a new one.",
                "code": "INVALID_TOKEN",
            }), 400
        user = UserRepository.find_by_id(conn, user_id)
        UserRepository.update_password(conn, user_id, hash_password(password))
        if user.role == "CUSTOMER" and user.status == "INACTIVE":
            # Opening the emailed link proves they own the address, so confirm it too.
            UserRepository.set_status(conn, user_id, "ACTIVE")

    session.clear()
    EmailService.send_account_change(user.first_name, user.email, ["Your password was reset"])
    return jsonify({"message": "Your password has been reset. You can now log in with your new password."})
