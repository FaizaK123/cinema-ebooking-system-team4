"""Server-side validation for every form.

The frontend validates too, but anyone can bypass a browser form, so the backend
checks everything again. Each function returns (clean_value, error_message);
error_message is None when the value is valid.
"""
import re
from datetime import date

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
}

PASSWORD_RULES = "Use at least 8 characters, including an uppercase letter, a lowercase letter and a number."

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def validate_name(value, label):
    name = _text(value)
    if not name:
        return name, f"{label} is required."
    if len(name) > 50:
        return name, f"{label} must be 50 characters or fewer."
    if not _NAME_RE.match(name):
        return name, f"{label} can only contain letters, spaces, hyphens and apostrophes."
    return name, None


def validate_email(value):
    email = _text(value).lower()
    if not email:
        return email, "Email address is required."
    if len(email) > 254 or not _EMAIL_RE.match(email):
        return email, "Enter a valid email address, like name@example.com."
    return email, None


def validate_phone(value):
    """Accepts formats like (706) 555-1234 and stores the 10 digits only."""
    digits = re.sub(r"\D", "", _text(value))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if not digits:
        return digits, "Phone number is required."
    if len(digits) != 10:
        return digits, "Enter a 10-digit phone number."
    return digits, None


def validate_password(value):
    password = value if isinstance(value, str) else ""
    if not password:
        return password, "Password is required."
    if (len(password) < 8 or len(password) > 128
            or not re.search(r"[A-Z]", password)
            or not re.search(r"[a-z]", password)
            or not re.search(r"\d", password)):
        return password, PASSWORD_RULES
    return password, None


def validate_address(data):
    """Returns (address_dict, errors_dict). Error keys are field names."""
    data = data if isinstance(data, dict) else {}
    errors = {}
    street = _text(data.get("street"))
    city = _text(data.get("city"))
    state = _text(data.get("state")).upper()
    zip_code = _text(data.get("zip"))

    if not street:
        errors["street"] = "Street is required."
    elif len(street) > 100:
        errors["street"] = "Street must be 100 characters or fewer."
    if not city:
        errors["city"] = "City is required."
    elif len(city) > 50 or not _NAME_RE.match(city):
        errors["city"] = "Enter a valid city name."
    if not state:
        errors["state"] = "State is required."
    elif state not in US_STATES:
        errors["state"] = "Enter a 2-letter US state code, like GA."
    if not zip_code:
        errors["zip"] = "Zip code is required."
    elif not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
        errors["zip"] = "Enter a 5-digit zip code."

    return {"street": street, "city": city, "state": state, "zip": zip_code}, errors


def _luhn_valid(number):
    """Standard checksum every real card number passes; catches typos."""
    total = 0
    for i, digit in enumerate(reversed(number)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _card_brand(number):
    if number.startswith("4"):
        return "Visa"
    if re.match(r"^(5[1-5]|2[2-7])", number):
        return "Mastercard"
    if re.match(r"^3[47]", number):
        return "American Express"
    if re.match(r"^(6011|65|64[4-9])", number):
        return "Discover"
    return "Card"


def validate_card(data):
    """Returns (card_dict, errors_dict).

    The CVV is checked for format here but is never stored anywhere.
    `expiration` is "YYYY-MM" (what an <input type="month"> sends).
    """
    data = data if isinstance(data, dict) else {}
    errors = {}
    holder = _text(data.get("cardholderName"))
    number = re.sub(r"[\s-]", "", _text(data.get("number")))
    expiration = _text(data.get("expiration"))
    cvv = _text(data.get("cvv"))
    exp_year = exp_month = None

    if not holder:
        errors["cardholderName"] = "Name on card is required."
    elif len(holder) > 60 or not _NAME_RE.match(holder):
        errors["cardholderName"] = "Enter the name exactly as it appears on the card."

    if not number:
        errors["number"] = "Card number is required."
    elif not number.isdigit() or not 13 <= len(number) <= 19 or not _luhn_valid(number):
        errors["number"] = "Enter a valid card number."

    match = re.fullmatch(r"(\d{4})-(\d{2})", expiration)
    if not expiration:
        errors["expiration"] = "Expiration date is required."
    elif not match or not 1 <= int(match.group(2)) <= 12:
        errors["expiration"] = "Enter the expiration month and year."
    else:
        exp_year, exp_month = int(match.group(1)), int(match.group(2))
        today = date.today()
        if (exp_year, exp_month) < (today.year, today.month):
            errors["expiration"] = "This card has expired."
        elif exp_year > today.year + 20:
            errors["expiration"] = "Enter a valid expiration year."

    if not cvv:
        errors["cvv"] = "Security code is required."
    elif not re.fullmatch(r"\d{3,4}", cvv):
        errors["cvv"] = "Enter the 3- or 4-digit security code."

    card = {
        "cardholderName": holder,
        "number": number,
        "brand": _card_brand(number) if number.isdigit() else "Card",
        "expMonth": exp_month,
        "expYear": exp_year,
    }
    return card, errors
