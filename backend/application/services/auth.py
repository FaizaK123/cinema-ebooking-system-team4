"""Authentication and account lifecycle use cases."""
import sqlite3
from datetime import datetime, timezone

from backend.application.services.results import ServiceResult
from backend.data_access.db import db_transaction, get_db_connection
from backend.data_access.repositories import (
    AddressRepository,
    CardRepository,
    TokenRepository,
    UserRepository,
    expiry,
)
from backend.infrastructure import config
from backend.infrastructure.email_service import EmailService
from backend.infrastructure.security import (
    encrypt_card_number,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from backend.infrastructure.validators import (
    validate_address,
    validate_card,
    validate_email,
    validate_name,
    validate_password,
    validate_phone,
)


def _errors_result(errors, status=400):
    return ServiceResult({"error": "Please fix the highlighted fields.", "errors": errors}, status)


def _send_verification(conn, user_id, first_name, email, host_url):
    token = new_token()
    TokenRepository.create(
        conn,
        user_id,
        TokenRepository.VERIFY_EMAIL,
        hash_token(token),
        expiry(hours=config.VERIFY_TOKEN_HOURS),
    )
    link = f"{host_url}api/auth/verify?token={token}"
    return lambda: EmailService.send_verification(first_name, email, link)


def register(data, host_url):
    errors = {}
    first_name, err = validate_name(data.get("firstName"), "First name")
    if err:
        errors["firstName"] = err
    last_name, err = validate_name(data.get("lastName"), "Last name")
    if err:
        errors["lastName"] = err
    email, err = validate_email(data.get("email"))
    if err:
        errors["email"] = err
    phone, err = validate_phone(data.get("phone"))
    if err:
        errors["phone"] = err
    password, err = validate_password(data.get("password"))
    if err:
        errors["password"] = err
    if not data.get("confirmPassword"):
        errors["confirmPassword"] = "Please confirm your password."
    elif data.get("confirmPassword") != data.get("password"):
        errors["confirmPassword"] = "Passwords don't match."

    address = None
    if data.get("address"):
        address, address_errors = validate_address(data["address"])
        errors.update({f"address.{field}": message for field, message in address_errors.items()})

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
        duplicate = (
            errors.get("email", "").startswith("An account")
            or errors.get("phone", "").startswith("This phone")
        )
        status = 409 if duplicate and set(errors) <= {"email", "phone"} else 400
        return _errors_result(errors, status)

    try:
        with db_transaction() as conn:
            user_id = UserRepository.create_customer(
                conn,
                first_name,
                last_name,
                email,
                phone,
                hash_password(password),
                bool(data.get("promoOptIn")),
            )
            if address:
                AddressRepository.save(conn, user_id, address)
            for card in cards:
                CardRepository.add(conn, user_id, card, encrypt_card_number(card["number"]))
            send_email = _send_verification(conn, user_id, first_name, email, host_url)
    except sqlite3.IntegrityError as error:
        if "users.email" in str(error):
            return _errors_result(
                {"email": "An account with this email already exists. Try logging in instead."}, 409
            )
        if "users.phone_num" in str(error):
            return _errors_result(
                {"phone": "This phone number is already linked to another account."}, 409
            )
        raise

    email_sent = send_email()
    if email_sent:
        message = (
            f"Account created! We sent a confirmation email to {email}. "
            "Click the link in it to activate your account, then log in."
        )
    else:
        message = (
            "Your account was created, but we couldn't send the confirmation email right now. "
            "Use 'Resend confirmation email' on the login page to try again."
        )
    return ServiceResult({"message": message, "emailSent": email_sent}, 201)


def verify_email(token):
    with db_transaction() as conn:
        user_id = (
            TokenRepository.consume(conn, hash_token(token), TokenRepository.VERIFY_EMAIL)
            if token else None
        )
        if user_id is None:
            return ServiceResult({"verified": False})
        user = UserRepository.find_by_id(conn, user_id)
        if user and user.status == "INACTIVE":
            UserRepository.set_status(conn, user_id, "ACTIVE")
    return ServiceResult({"verified": True})


def resend_verification(email, host_url):
    email, err = validate_email(email)
    if err:
        return _errors_result({"email": err})

    send_email = None
    with db_transaction() as conn:
        user = UserRepository.find_by_email(conn, email)
        if user and user.role == "CUSTOMER" and user.status == "INACTIVE":
            send_email = _send_verification(
                conn, user.id, user.first_name, user.email, host_url
            )
    if send_email:
        send_email()
    return ServiceResult({
        "message": "If that account still needs to be confirmed, we've sent a new confirmation link."
    })


def login(identifier, password, remember):
    identifier = (identifier or "").strip()
    password = password or ""
    errors = {}
    if not identifier:
        errors["identifier"] = "Enter your email address or phone number."
    if not password:
        errors["password"] = "Enter your password."
    if errors:
        return _errors_result(errors)

    conn = get_db_connection()
    try:
        if "@" in identifier:
            user = UserRepository.find_by_email(conn, identifier.lower())
        else:
            phone, _ = validate_phone(identifier)
            user = UserRepository.find_by_phone(conn, phone) if phone else None
    finally:
        conn.close()

    if user is None or not verify_password(user.password_hash, password):
        return ServiceResult(
            {"error": "Incorrect email/phone number or password. Please try again."}, 401
        )
    if user.role == "CUSTOMER" and user.status == "INACTIVE":
        return ServiceResult({
            "error": "Account is not verified. Please check your email to verify your account.",
            "code": "UNVERIFIED",
            "email": user.email,
        }, 403)
    if user.role == "CUSTOMER" and user.status == "SUSPENDED":
        return ServiceResult({
            "error": "This account has been suspended. Please contact the theater for help.",
            "code": "SUSPENDED",
        }, 403)
    return ServiceResult({"user": user, "remember": bool(remember)})


def forgot_password(email, host_url):
    email, err = validate_email(email)
    if err:
        return _errors_result({"email": err})

    send_email = None
    with db_transaction() as conn:
        user = UserRepository.find_by_email(conn, email)
        if user and user.status != "SUSPENDED":
            token = new_token()
            TokenRepository.create(
                conn,
                user.id,
                TokenRepository.RESET_PASSWORD,
                hash_token(token),
                expiry(minutes=config.RESET_TOKEN_MINUTES),
            )
            link = f"{host_url}Forgot_Password.html?token={token}"
            send_email = lambda: EmailService.send_password_reset(user.first_name, user.email, link)
    if send_email:
        send_email()
    return ServiceResult({
        "message": (
            f"If an account exists for {email}, we've sent a password reset link. "
            f"It expires in {config.RESET_TOKEN_MINUTES} minutes."
        )
    })


def check_reset_token(token):
    conn = get_db_connection()
    try:
        valid = TokenRepository.is_valid(
            conn, hash_token(token), TokenRepository.RESET_PASSWORD, datetime.now(timezone.utc)
        )
    finally:
        conn.close()
    return ServiceResult({"valid": valid})


def reset_password(data):
    token = data.get("token") or ""
    password, err = validate_password(data.get("password"))
    errors = {}
    if err:
        errors["password"] = err
    if data.get("confirmPassword") != data.get("password"):
        errors["confirmPassword"] = "Passwords don't match."
    if errors:
        return _errors_result(errors)

    with db_transaction() as conn:
        user_id = (
            TokenRepository.consume(conn, hash_token(token), TokenRepository.RESET_PASSWORD)
            if token else None
        )
        if user_id is None:
            return ServiceResult({
                "error": "This reset link is invalid or has expired. Please request a new one.",
                "code": "INVALID_TOKEN",
            }, 400)
        user = UserRepository.find_by_id(conn, user_id)
        UserRepository.update_password(conn, user_id, hash_password(password))
        if user.role == "CUSTOMER" and user.status == "INACTIVE":
            UserRepository.set_status(conn, user_id, "ACTIVE")

    EmailService.send_account_change(user.first_name, user.email, ["Your password was reset"])
    return ServiceResult({
        "message": "Your password has been reset. You can now log in with your new password."
    })
