"""Server-side validation for every form.

The frontend validates too, but anyone can bypass a browser form, so the backend
checks everything again. Each function returns (clean_value, error_message);
error_message is None when the value is valid.
"""
import re
from datetime import date, datetime

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


# ---------------------------------------------------------------- Sprint 3: movies, showtimes, promotions, tickets

MOVIE_RATINGS = ["G", "PG", "PG-13", "R", "NC-17"]
MOVIE_STATUSES = ("CURRENTLY_RUNNING", "COMING_SOON")
TICKET_CATEGORIES = ("ADULT", "CHILD", "SENIOR")
MAX_TICKETS_PER_TYPE = 100  # only guards against absurd numbers; the real limit is the seats left

_GENRE_RE = re.compile(r"^[A-Za-z][A-Za-z '\-]*$")
_TRAILER_RE = re.compile(r"^https://www\.youtube(-nocookie)?\.com/embed/[A-Za-z0-9_-]{6,20}(\?[A-Za-z0-9=&_.-]*)?$")
_PROMO_CODE_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")
_PNG_START = b"\x89PNG\r\n\x1a\n"
_JPEG_START = b"\xff\xd8\xff"


def whole_number(value):
    """int for 5 or "5" (what JSON or a form sends), None for anything else (True, 2.5, "abc")."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{1,9}", value.strip()):
        return int(value.strip())
    return None


def parse_iso_date(text):
    """'2026-11-20' -> date, or None. Only the exact YYYY-MM-DD form an HTML date input sends is accepted."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def parse_hhmm(text):
    """'14:30' or '14:30:00' (what an HTML time input sends) -> '14:30', or None."""
    for pattern in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).strftime("%H:%M")
        except ValueError:
            continue
    return None


def _has_control_chars(text):
    return any(ord(char) < 32 or ord(char) == 127 for char in text)


def validate_poster(file_storage, max_bytes):
    """Returns (image_bytes, extension, error). Checks the file's real contents, not just its name."""
    if file_storage is None or not getattr(file_storage, "filename", ""):
        return None, None, "A movie poster is required."
    content = file_storage.read(max_bytes + 1)
    if not content:
        return None, None, "The poster file is empty."
    if len(content) > max_bytes:
        return None, None, f"The poster must be {max_bytes // (1024 * 1024)} MB or smaller."
    if content.startswith(_PNG_START):
        return content, ".png", None
    if content.startswith(_JPEG_START):
        return content, ".jpg", None
    return None, None, "Please choose a JPG or PNG image."


def validate_movie(data, today=None):
    """Returns (movie_dict, errors_dict) for the Add Movie form. Error keys are the form's field names."""
    data = data if isinstance(data, dict) else {}
    today = today or date.today()
    errors = {}

    title = " ".join(_text(data.get("title")).split())
    if not title:
        errors["title"] = "Movie title is required."
    elif len(title) > 150 or _has_control_chars(title):
        errors["title"] = "Movie title must be 150 characters or fewer."

    description = _text(data.get("description"))
    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 2000:
        errors["description"] = "Description must be 2000 characters or fewer."

    release_text = _text(data.get("releaseDate"))
    release_date = None
    if not release_text:
        errors["releaseDate"] = "Release date is required."
    else:
        release_date = parse_iso_date(release_text)
        if release_date is None or release_date.year < 1888:
            release_date = None
            errors["releaseDate"] = "Enter a valid release date."

    minutes = whole_number(data.get("duration"))
    if data.get("duration") in (None, ""):
        errors["duration"] = "Duration is required."
    elif minutes is None or not 1 <= minutes <= 600:
        errors["duration"] = "Enter the duration as a whole number of minutes (1-600)."

    rating = _text(data.get("rating")).upper()
    if not rating:
        errors["rating"] = "Rating is required."
    elif rating not in MOVIE_RATINGS:
        errors["rating"] = "Choose one of: " + ", ".join(MOVIE_RATINGS) + "."

    genres = []
    raw_genres = data.get("genres")
    if isinstance(raw_genres, str):
        raw_genres = [raw_genres]
    if not isinstance(raw_genres, list):
        raw_genres = []
    for raw in raw_genres:
        for part in str(raw).split(","):
            genre = " ".join(part.split())
            if not genre:
                continue
            if len(genre) > 30 or not _GENRE_RE.match(genre):
                errors["genres"] = "Genres can only contain letters, spaces and hyphens (30 characters max each)."
                break
            genre = re.sub(r"(^|[ -])([a-z])", lambda m: m.group(1) + m.group(2).upper(), genre)
            if genre.lower() not in [g.lower() for g in genres]:
                genres.append(genre)
    if not genres and "genres" not in errors:
        errors["genres"] = "Add at least one genre."

    trailer = _text(data.get("trailer")) or None
    if trailer and not _TRAILER_RE.match(trailer):
        errors["trailer"] = "Use a YouTube embed link, like https://www.youtube.com/embed/VIDEO_ID."

    status = _text(data.get("status")).upper()
    if status and status not in MOVIE_STATUSES:
        errors["status"] = "Status must be CURRENTLY_RUNNING or COMING_SOON."
    elif not status and release_date:
        status = "CURRENTLY_RUNNING" if release_date <= today else "COMING_SOON"

    movie = {
        "title": title,
        "description": description,
        "releaseDate": release_date.isoformat() if release_date else release_text,
        "duration": minutes,
        "rating": rating,
        "genre": ", ".join(genres),
        "trailer": trailer,
        "status": status,
    }
    return movie, errors


def validate_showtime(data, now):
    """Returns (showtime_dict, errors_dict) for scheduling a movie. `now` is the cinema's local datetime."""
    data = data if isinstance(data, dict) else {}
    errors = {}

    movie_id = whole_number(data.get("movieId"))
    if data.get("movieId") in (None, ""):
        errors["movieId"] = "Select a movie."
    elif movie_id is None:
        errors["movieId"] = "Select a valid movie."

    show_date = None
    date_text = _text(data.get("date"))
    if not date_text:
        errors["date"] = "Date is required."
    else:
        show_date = parse_iso_date(date_text)
        if show_date is None:
            errors["date"] = "Enter a valid date."

    show_time = None
    time_text = _text(data.get("time"))
    if not time_text:
        errors["time"] = "Time is required."
    else:
        show_time = parse_hhmm(time_text)
        if show_time is None:
            errors["time"] = "Enter a valid time."

    room_id = whole_number(data.get("showroomId"))
    if data.get("showroomId") in (None, ""):
        errors["showroomId"] = "Select a showroom."
    elif room_id is None:
        errors["showroomId"] = "Select a valid showroom."

    if show_date and show_time and "date" not in errors and "time" not in errors:
        if datetime.strptime(f"{show_date.isoformat()} {show_time}", "%Y-%m-%d %H:%M") <= now:
            errors["date"] = "The showtime must be in the future. Pick a later date or time."

    showtime = {
        "movieId": movie_id,
        "date": show_date.isoformat() if show_date else date_text,
        "time": show_time or time_text,
        "showroomId": room_id,
    }
    return showtime, errors


def validate_promotion(data, today=None):
    """Returns (promotion_dict, errors_dict). The discount is a whole percent from 1 to 100."""
    data = data if isinstance(data, dict) else {}
    today = today or date.today()
    errors = {}

    code = _text(data.get("promoCode")).upper()
    if not code:
        errors["promoCode"] = "Promotion code is required."
    elif not _PROMO_CODE_RE.match(code):
        errors["promoCode"] = "Use 3-20 letters, numbers, hyphens or underscores."

    percent = whole_number(data.get("discountPercent"))
    if data.get("discountPercent") in (None, ""):
        errors["discountPercent"] = "Discount is required."
    elif percent is None or not 1 <= percent <= 100:
        errors["discountPercent"] = "Enter a whole-number discount from 1 to 100."

    description = _text(data.get("description"))
    if not description:
        errors["description"] = "Description is required."
    elif len(description) > 500:
        errors["description"] = "Description must be 500 characters or fewer."

    dates = {}
    for field, label in (("startDate", "Start date"), ("endDate", "End date")):
        text = _text(data.get(field))
        if not text:
            errors[field] = f"{label} is required."
            continue
        dates[field] = parse_iso_date(text)
        if dates[field] is None:
            errors[field] = f"Enter a valid {label.lower()}."
    if "startDate" not in errors and dates["startDate"] < today:
        errors["startDate"] = "The start date can't be in the past."
    if "startDate" not in errors and "endDate" not in errors and dates["endDate"] < dates["startDate"]:
        errors["endDate"] = "The end date can't be before the start date."

    subject = _text(data.get("emailSubject"))
    if not subject:
        errors["emailSubject"] = "Email subject is required."
    elif len(subject) > 150 or _has_control_chars(subject):
        errors["emailSubject"] = "Email subject must be 150 characters or fewer, on one line."

    body = _text(data.get("emailBody"))
    if not body:
        errors["emailBody"] = "Email message is required."
    elif len(body) > 5000:
        errors["emailBody"] = "Email message must be 5000 characters or fewer."

    promotion = {
        "promoCode": code,
        "discountPercent": percent,
        "description": description,
        "startDate": dates["startDate"].isoformat() if dates.get("startDate") else "",
        "endDate": dates["endDate"].isoformat() if dates.get("endDate") else "",
        "emailSubject": subject,
        "emailBody": body,
    }
    return promotion, errors


def validate_ticket_counts(data):
    """Returns ({'ADULT': n, 'CHILD': n, 'SENIOR': n}, errors_dict).

    `data` looks like {"adult": 2, "child": 1, "senior": 0}. Missing types count as 0.
    """
    data = data if isinstance(data, dict) else {}
    counts = {}
    errors = {}
    for category in TICKET_CATEGORIES:
        raw = data.get(category.lower(), 0)
        if raw in (None, ""):
            raw = 0
        number = whole_number(raw)
        if number is None or not 0 <= number <= MAX_TICKETS_PER_TYPE:
            errors[category.lower()] = f"Enter a whole number of {category.lower()} tickets (0 or more)."
            number = 0
        counts[category] = number
    if not errors and sum(counts.values()) < 1:
        errors["tickets"] = "Choose at least one ticket."
    return counts, errors
