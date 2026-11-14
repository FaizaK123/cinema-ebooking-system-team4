"""Date and time helpers shared by showtimes, seat holds and promotions.

Showtimes are stored the way an HTML form sends them: show_date "YYYY-MM-DD" and
show_time "HH:MM" (24-hour). They are the cinema's local time, so "now" for a
showtime means the server's local clock. Seat-hold expiry uses UTC instead.
"""
from datetime import datetime, timedelta, timezone

_UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # fixed width, so these strings sort in time order


def local_now():
    return datetime.now()


def utc_now_iso():
    return datetime.now(timezone.utc).strftime(_UTC_FORMAT)


def utc_iso_in(minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(_UTC_FORMAT)


def time_label(hhmm):
    """'14:30' -> '2:30 PM'"""
    return datetime.strptime(hhmm, "%H:%M").strftime("%I:%M %p").lstrip("0")


def runtime_label(minutes):
    """150 -> '2 hr 30 min', 120 -> '2 hr', 45 -> '45 min' (the format the seeded movies use)."""
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} hr {rest} min"
    if hours:
        return f"{hours} hr"
    return f"{rest} min"
