"""Seed demo data: movies, then showtimes in the 3 showrooms with a few already-booked seats.

Run from the project root (run.bat / run.sh do this on every start):
    python -m backend.scripts.seed_db

Safe to run again: movies are matched by title, showtimes by showroom + date + time, and a
showtime's pre-booked seats are only created together with the showtime itself.
"""
import secrets
import sqlite3
from datetime import date, timedelta

from backend.data_access.db import db_transaction
from backend.data_access.repositories import ShowRepository, UserRepository
from backend.infrastructure import config
from backend.infrastructure.security import hash_password

MOVIE_ROWS = [
    ("The Odyssey", "Adventure", "R", "Odysseus faces a dangerous journey home after the Trojan War.", "/images/odyssey.jpg", "https://www.youtube.com/embed/vyCVVjA28fo", "CURRENTLY_RUNNING", "2026-07-17", "2 hr 52 min"),
    ("Jaws", "Horror", "PG", "A shark terrorizes a beach town.", "/images/jaws.jpg", "https://www.youtube.com/embed/U1fu_sA7XhE", "CURRENTLY_RUNNING", "1975-06-20", "2 hr 4 min"),
    ("The Silence of the Lambs", "Thriller", "R", "An FBI trainee seeks help from an imprisoned killer.", "/images/silenceOfTheLambs.jpg", "https://www.youtube.com/embed/6iB21hsprAQ", "CURRENTLY_RUNNING", "1991-02-14", "1 hr 58 min"),
    ("Dune: Part Two", "Sci-Fi", "PG-13", "Paul Atreides unites with Chani and the Fremen while seeking revenge for his family.", "/images/dunePartTwo.jpg", "https://www.youtube.com/embed/Way9Dexny3w", "CURRENTLY_RUNNING", "2024-03-01", "2 hr 46 min"),
    ("Oppenheimer", "Drama", "R", "The story of physicist J. Robert Oppenheimer and the creation of the atomic bomb.", "/images/oppenheimer.jpg", "https://www.youtube.com/embed/bK6ldnjE3Y0", "CURRENTLY_RUNNING", "2023-07-21", "3 hr"),
    ("Spider-Man: Across the Spider-Verse", "Animation", "PG", "Miles Morales travels across the multiverse and encounters a team of Spider-People.", "/images/spiderVerse.jpg", "https://www.youtube.com/embed/shW9i6k8cB0", "CURRENTLY_RUNNING", "2023-06-02", "2 hr 20 min"),
    ("Verity", "Thriller", "R", "A writer discovers disturbing secrets while completing another author's unfinished work.", "/images/verity.jpg", "https://www.youtube.com/embed/xdPMKhjMSFs", "COMING_SOON", "2026-10-02", "TBD"),
    ("The Cat in the Hat", "Animation", "PG", "The Cat in the Hat brings his unpredictable adventures to a new animated story.", "/images/catInTheHat.jpg", "https://www.youtube.com/embed/HT5JAp5z0-o", "COMING_SOON", "2026-11-06", "TBD"),
    ("The Hunger Games: Sunrise on the Reaping", "Adventure", "TBD", "A new Hunger Games story set decades before Katniss Everdeen's rebellion.", "/images/sunriseOnTheReaping.jpg", "https://www.youtube.com/embed/fS35YSjopjE", "COMING_SOON", "2026-11-20", "TBD"),
    ("Avengers: Doomsday", "Action", "TBD", "The Avengers return to face a new threat to the Marvel universe.", "/images/avengersDoomsday.jpg", "https://www.youtube.com/embed/fxNh27fRdYA", "COMING_SOON", "2026-12-18", "TBD"),
    ("Dune: Part Three", "Sci-Fi", "TBD", "The next chapter in Paul Atreides' journey continues the Dune saga.", "/images/dunePartThree.jpg", "https://www.youtube.com/embed/rGNc8RRggzo", "COMING_SOON", "2026-12-18", "TBD"),
    ("Clayface", "Horror", "TBD", "A new story centered on the shape-shifting DC character Clayface.", "/images/clayface.jpg", "https://www.youtube.com/embed/OGO4Mqvo3jI", "COMING_SOON", "2026-10-23", "TBD"),
]

SHOWTIME_DAYS = 7  # today and the next 6 days
# Start times are deliberately not round numbers, so an admin demoing the scheduler can pick
# 2:00 PM, 5:00 PM or 8:00 PM in any showroom without running into the seeded showtimes.
SLOTS = ["12:15", "14:45", "17:20", "19:50", "22:25"]
SEED_BOOKER_EMAIL = "seed-bookings@ces.local"  # owns the pre-booked seats; suspended, so nobody can log in as it


def seed_movies(conn):
    added = 0
    for movie in MOVIE_ROWS:
        if conn.execute("SELECT 1 FROM movies WHERE title = ?", (movie[0],)).fetchone() is None:
            conn.execute(
                "INSERT INTO movies (title, genre, rating, description, poster, trailer, status, release_date, runtime) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                movie,
            )
            added += 1
    return added


def _seed_booker_id(conn):
    user = UserRepository.find_by_email(conn, SEED_BOOKER_EMAIL)
    if user:
        return user.id
    user_id = UserRepository.create_customer(
        conn, "Existing", "Bookings", SEED_BOOKER_EMAIL, None, hash_password(secrets.token_urlsafe(24)), False
    )
    UserRepository.set_status(conn, user_id, "SUSPENDED")
    return user_id


def _book_some_seats(conn, show_id, booker_id, adult_type_id, adult_price):
    """Mark about one seat in seven as already booked, with a real booking, tickets and payment behind it."""
    seat_rows = conn.execute(
        "SELECT show_seat_id FROM show_seats WHERE show_id = ? AND (seat_id + ?) % 7 = 0 ORDER BY seat_id",
        (show_id, show_id),
    ).fetchall()
    if not seat_rows:
        return 0
    total = round(adult_price * len(seat_rows), 2)
    booking_id = conn.execute(
        "INSERT INTO bookings (customer_id, status, total_amount) VALUES (?, 'CONFIRMED', ?)", (booker_id, total)
    ).lastrowid
    for row in seat_rows:
        conn.execute("UPDATE show_seats SET status = 'BOOKED' WHERE show_seat_id = ?", (row["show_seat_id"],))
        conn.execute(
            "INSERT INTO tickets (booking_id, show_seat_id, ticket_type_id, price_paid) VALUES (?, ?, ?, ?)",
            (booking_id, row["show_seat_id"], adult_type_id, adult_price),
        )
    conn.execute(
        "INSERT INTO payments (booking_id, amount, status, paid_at, provider_reference) "
        "VALUES (?, ?, 'PAID', datetime('now'), ?)",
        (booking_id, total, f"SEED-SHOW-{show_id}"),
    )
    return len(seat_rows)


def seed_showtimes(conn):
    """Schedule every currently running movie twice a day across the 3 showrooms for a week."""
    movies = conn.execute("SELECT id FROM movies WHERE status = 'CURRENTLY_RUNNING' ORDER BY id").fetchall()
    rooms = conn.execute("SELECT room_id FROM showrooms ORDER BY room_number").fetchall()
    adult = conn.execute("SELECT ticket_type_id, price FROM ticket_types WHERE category = 'ADULT'").fetchone()
    if not movies or len(rooms) < 3 or adult is None:
        print("Skipping showtimes: run backend.scripts.init_db first (it creates the showrooms and ticket types).")
        return 0, 0

    booker_id = None
    created = booked = 0
    for offset in range(SHOWTIME_DAYS):
        day = date.today() + timedelta(days=offset)
        # 12 showings a day (2 per movie). Showings are spread over the 3 showrooms and each showroom gets
        # distinct start times (rotating with the date), so seeded showtimes never conflict with each other.
        for number in range(2 * len(movies)):
            movie_id = movies[number % len(movies)]["id"]
            # a movie's second showing of the day is in the next showroom over
            room_id = rooms[(number % 3 + number // len(movies)) % 3]["room_id"]
            slot = SLOTS[(number // 3 + day.toordinal()) % len(SLOTS)]
            if ShowRepository.find_in_room_at(conn, room_id, day.isoformat(), slot):
                continue
            try:
                show_id = ShowRepository.create(conn, movie_id, room_id, day.isoformat(), slot)
            except sqlite3.IntegrityError:
                continue
            created += 1
            booker_id = booker_id or _seed_booker_id(conn)
            booked += _book_some_seats(conn, show_id, booker_id, adult["ticket_type_id"], adult["price"])
    return created, booked


def main():
    with db_transaction() as conn:
        movies_added = seed_movies(conn)
        shows_created, seats_booked = seed_showtimes(conn)
    print(f"Database: {config.DB_PATH}")
    print(f"Movies added: {movies_added}")
    print(f"Showtimes added: {shows_created} ({seats_booked} seats pre-booked)")


if __name__ == "__main__":
    main()
