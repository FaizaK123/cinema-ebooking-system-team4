"""Data access layer: every SQL query for users, addresses, cards, tokens and favorites.

Routes call these classes instead of writing SQL themselves, so the database
details live in one place. Each method takes an open connection, which lets a
route group several calls into one transaction.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from backend.infrastructure.timeutil import time_label


@dataclass
class User:
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str
    status: str            # ACTIVE / INACTIVE / SUSPENDED for customers; ACTIVE for admins
    promo_opt_in: bool
    password_hash: str

    def to_public_dict(self):
        """What the frontend may see. Never includes the password hash."""
        return {
            "id": self.id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "promoOptIn": self.promo_opt_in,
        }


_USER_SELECT = """
    SELECT u.user_id, u.first_name, u.last_name, u.email, u.phone_num, u.role,
           u.password_hash, u.promo_opt_in, c.status
    FROM users u
    LEFT JOIN customers c ON c.customer_id = u.user_id
"""


def _row_to_user(row):
    if row is None:
        return None
    return User(
        id=row["user_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone_num"],
        role=row["role"],
        status=row["status"] or "ACTIVE",
        promo_opt_in=bool(row["promo_opt_in"]),
        password_hash=row["password_hash"],
    )


def _utc_now():
    return datetime.now(timezone.utc)


class UserRepository:
    @staticmethod
    def find_by_id(conn, user_id):
        return _row_to_user(conn.execute(_USER_SELECT + " WHERE u.user_id = ?", (user_id,)).fetchone())

    @staticmethod
    def find_by_email(conn, email):
        return _row_to_user(conn.execute(_USER_SELECT + " WHERE u.email = ?", (email,)).fetchone())

    @staticmethod
    def find_by_phone(conn, phone):
        return _row_to_user(conn.execute(_USER_SELECT + " WHERE u.phone_num = ?", (phone,)).fetchone())

    @staticmethod
    def create_customer(conn, first_name, last_name, email, phone, password_hash, promo_opt_in):
        """New customers start INACTIVE until they confirm their email."""
        cursor = conn.execute(
            "INSERT INTO users (first_name, last_name, email, phone_num, password_hash, role, promo_opt_in) "
            "VALUES (?, ?, ?, ?, ?, 'CUSTOMER', ?)",
            (first_name, last_name, email, phone, password_hash, int(promo_opt_in)),
        )
        user_id = cursor.lastrowid
        conn.execute("INSERT INTO customers (customer_id, status) VALUES (?, 'INACTIVE')", (user_id,))
        return user_id

    @staticmethod
    def set_status(conn, user_id, status):
        conn.execute("UPDATE customers SET status = ? WHERE customer_id = ?", (status, user_id))

    @staticmethod
    def update_profile(conn, user_id, first_name, last_name, phone, promo_opt_in):
        conn.execute(
            "UPDATE users SET first_name = ?, last_name = ?, phone_num = ?, promo_opt_in = ? WHERE user_id = ?",
            (first_name, last_name, phone, int(promo_opt_in), user_id),
        )

    @staticmethod
    def update_password(conn, user_id, password_hash):
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = ?", (password_hash, user_id))


class AddressRepository:
    @staticmethod
    def get(conn, customer_id):
        row = conn.execute(
            "SELECT street, city, state, zip FROM addresses WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def save(conn, customer_id, address):
        """Each customer has at most one address, so this replaces any existing one."""
        conn.execute("DELETE FROM addresses WHERE customer_id = ?", (customer_id,))
        conn.execute(
            "INSERT INTO addresses (customer_id, street, city, state, zip) VALUES (?, ?, ?, ?, ?)",
            (customer_id, address["street"], address["city"], address["state"], address["zip"]),
        )

    @staticmethod
    def delete(conn, customer_id):
        return conn.execute("DELETE FROM addresses WHERE customer_id = ?", (customer_id,)).rowcount > 0


class CardRepository:
    @staticmethod
    def list(conn, customer_id):
        rows = conn.execute(
            "SELECT card_id, card_brand, last_four, expiration_month, expiration_year, cardholder_name "
            "FROM payment_cards WHERE customer_id = ? ORDER BY card_id",
            (customer_id,),
        ).fetchall()
        return [
            {
                "id": row["card_id"],
                "brand": row["card_brand"],
                "lastFour": row["last_four"],
                "expMonth": row["expiration_month"],
                "expYear": row["expiration_year"],
                "cardholderName": row["cardholder_name"],
            }
            for row in rows
        ]

    @staticmethod
    def count(conn, customer_id):
        return conn.execute(
            "SELECT COUNT(*) FROM payment_cards WHERE customer_id = ?", (customer_id,)
        ).fetchone()[0]

    @staticmethod
    def add(conn, customer_id, card, encrypted_number):
        """`card` is already validated. Only the encrypted number and last four digits are stored; never the CVV."""
        conn.execute(
            "INSERT INTO payment_cards (customer_id, cardholder_name, card_brand, last_four, "
            "card_number_encrypted, expiration_month, expiration_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                customer_id,
                card["cardholderName"],
                card["brand"],
                card["number"][-4:],
                encrypted_number,
                card["expMonth"],
                card["expYear"],
            ),
        )

    @staticmethod
    def delete(conn, customer_id, card_id):
        """The customer_id check stops one user from deleting another user's card."""
        return conn.execute(
            "DELETE FROM payment_cards WHERE card_id = ? AND customer_id = ?", (card_id, customer_id)
        ).rowcount > 0


class TokenRepository:
    VERIFY_EMAIL = "VERIFY_EMAIL"
    RESET_PASSWORD = "RESET_PASSWORD"

    @staticmethod
    def create(conn, user_id, purpose, token_hash, lifetime):
        """Store a new token and cancel older unused tokens for the same purpose."""
        conn.execute(
            "UPDATE auth_tokens SET used_at = ? WHERE user_id = ? AND purpose = ? AND used_at IS NULL",
            (_utc_now().isoformat(), user_id, purpose),
        )
        conn.execute(
            "INSERT INTO auth_tokens (user_id, token_hash, purpose, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, token_hash, purpose, (_utc_now() + lifetime).isoformat()),
        )

    @staticmethod
    def consume(conn, token_hash, purpose):
        """Return the token's user_id and mark it used, or None if it's unknown, used or expired."""
        row = conn.execute(
            "SELECT token_id, user_id, expires_at, used_at FROM auth_tokens WHERE token_hash = ? AND purpose = ?",
            (token_hash, purpose),
        ).fetchone()
        if row is None or row["used_at"] is not None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _utc_now():
            return None
        conn.execute("UPDATE auth_tokens SET used_at = ? WHERE token_id = ?", (_utc_now().isoformat(), row["token_id"]))
        return row["user_id"]

    @staticmethod
    def is_valid(conn, token_hash, purpose, now):
        row = conn.execute(
            "SELECT expires_at, used_at FROM auth_tokens WHERE token_hash = ? AND purpose = ?",
            (token_hash, purpose),
        ).fetchone()
        return bool(
            row
            and row["used_at"] is None
            and datetime.fromisoformat(row["expires_at"]) > now
        )


class FavoriteRepository:
    @staticmethod
    def list_movies(conn, customer_id):
        return conn.execute(
            "SELECT m.* FROM preferences p JOIN movies m ON m.id = p.favorite_movie_id "
            "WHERE p.customer_id = ? AND p.favorite_movie_id IS NOT NULL ORDER BY p.preference_id",
            (customer_id,),
        ).fetchall()

    @staticmethod
    def add_movie(conn, customer_id, movie_id):
        exists = conn.execute(
            "SELECT 1 FROM preferences WHERE customer_id = ? AND favorite_movie_id = ?", (customer_id, movie_id)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO preferences (customer_id, favorite_movie_id) VALUES (?, ?)", (customer_id, movie_id)
            )

    @staticmethod
    def remove_movie(conn, customer_id, movie_id):
        return conn.execute(
            "DELETE FROM preferences WHERE customer_id = ? AND favorite_movie_id = ?", (customer_id, movie_id)
        ).rowcount > 0

    @staticmethod
    def list_genres(conn, customer_id):
        rows = conn.execute(
            "SELECT favorite_genre FROM preferences WHERE customer_id = ? AND favorite_genre IS NOT NULL "
            "ORDER BY favorite_genre",
            (customer_id,),
        ).fetchall()
        return [row["favorite_genre"] for row in rows]

    @staticmethod
    def replace_genres(conn, customer_id, genres):
        conn.execute("DELETE FROM preferences WHERE customer_id = ? AND favorite_genre IS NOT NULL", (customer_id,))
        conn.executemany(
            "INSERT INTO preferences (customer_id, favorite_genre) VALUES (?, ?)",
            [(customer_id, genre) for genre in genres],
        )


class MovieRepository:
    """A movie's `genre` column holds one or more genres separated by commas ("Action, Sci-Fi")."""

    @staticmethod
    def _split_genres(value):
        return [part.strip() for part in (value or "").split(",") if part.strip()]

    @staticmethod
    def search(conn, title=None, genres=None):
        query = "SELECT * FROM movies"
        params = []
        if title:
            query += " WHERE title LIKE ?"
            params.append(f"%{title}%")
        rows = conn.execute(query, params).fetchall()
        if genres:
            wanted = {genre.lower() for genre in genres}
            rows = [
                row for row in rows
                if wanted & {g.lower() for g in MovieRepository._split_genres(row["genre"])}
            ]
        return rows

    @staticmethod
    def find(conn, movie_id):
        return conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()

    @staticmethod
    def genres(conn):
        names = {}
        for row in conn.execute("SELECT genre FROM movies WHERE genre IS NOT NULL AND genre != ''"):
            for genre in MovieRepository._split_genres(row["genre"]):
                names.setdefault(genre.lower(), genre)
        return sorted(names.values(), key=str.lower)

    @staticmethod
    def title_exists(conn, title):
        return conn.execute("SELECT 1 FROM movies WHERE LOWER(title) = LOWER(?)", (title,)).fetchone() is not None

    @staticmethod
    def create(conn, movie):
        cursor = conn.execute(
            "INSERT INTO movies (title, genre, rating, description, poster, trailer, status, release_date, runtime) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                movie["title"], movie["genre"], movie["rating"], movie["description"], movie["poster"],
                movie["trailer"], movie["status"], movie["releaseDate"], movie["runtime"],
            ),
        )
        return cursor.lastrowid


class AdminRepository:
    @staticmethod
    def summary(conn):
        return {
            "movies": conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
            "currentlyRunning": conn.execute(
                "SELECT COUNT(*) FROM movies WHERE status = 'CURRENTLY_RUNNING'"
            ).fetchone()[0],
            "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
            "activeCustomers": conn.execute(
                "SELECT COUNT(*) FROM customers WHERE status = 'ACTIVE'"
            ).fetchone()[0],
            "promotions": conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0],
        }


class ShowroomRepository:
    @staticmethod
    def list_all(conn):
        rows = conn.execute(
            "SELECT r.room_id, r.room_number, t.name AS theater, COUNT(se.seat_id) AS capacity, "
            "COUNT(DISTINCT se.row_label) AS seat_rows, MAX(se.seat_number) AS seats_per_row "
            "FROM showrooms r JOIN theaters t ON t.theater_id = r.theater_id "
            "LEFT JOIN seats se ON se.room_id = r.room_id "
            "GROUP BY r.room_id ORDER BY r.room_number"
        ).fetchall()
        return [
            {
                "id": row["room_id"],
                "name": f"Showroom {row['room_number']}",
                "theater": row["theater"],
                "capacity": row["capacity"],
                "rows": row["seat_rows"],
                "seatsPerRow": row["seats_per_row"],
            }
            for row in rows
        ]

    @staticmethod
    def find(conn, room_id):
        return conn.execute("SELECT room_id, room_number FROM showrooms WHERE room_id = ?", (room_id,)).fetchone()

    @staticmethod
    def busy_room_ids(conn, show_date, show_time):
        rows = conn.execute(
            "SELECT room_id FROM shows WHERE show_date = ? AND show_time = ?", (show_date, show_time)
        ).fetchall()
        return {row["room_id"] for row in rows}


_SHOW_SELECT = (
    "SELECT s.show_id, s.movie_id, m.title, s.show_date, s.show_time, s.room_id, r.room_number "
    "FROM shows s JOIN movies m ON m.id = s.movie_id JOIN showrooms r ON r.room_id = s.room_id"
)
_UPCOMING = "(s.show_date > ? OR (s.show_date = ? AND s.show_time > ?))"


def _show_dict(row):
    return {
        "showId": row["show_id"],
        "movieId": row["movie_id"],
        "movieTitle": row["title"],
        "date": row["show_date"],
        "time": row["show_time"],
        "timeLabel": time_label(row["show_time"]),
        "showroomId": row["room_id"],
        "showroom": f"Showroom {row['room_number']}",
    }


def _upcoming_params(now):
    return (now.date().isoformat(), now.date().isoformat(), now.strftime("%H:%M"))


class ShowRepository:
    @staticmethod
    def find(conn, show_id):
        row = conn.execute(_SHOW_SELECT + " WHERE s.show_id = ?", (show_id,)).fetchone()
        return _show_dict(row) if row else None

    @staticmethod
    def list_upcoming_for_movie(conn, movie_id, now):
        rows = conn.execute(
            _SHOW_SELECT + f" WHERE s.movie_id = ? AND {_UPCOMING} ORDER BY s.show_date, s.show_time, r.room_number",
            (movie_id, *_upcoming_params(now)),
        ).fetchall()
        return [_show_dict(row) for row in rows]

    @staticmethod
    def upcoming_by_movie(conn, now):
        """{movie_id: [show, ...]} for every movie that has upcoming showtimes."""
        rows = conn.execute(
            _SHOW_SELECT + f" WHERE {_UPCOMING} ORDER BY s.show_date, s.show_time, r.room_number",
            _upcoming_params(now),
        ).fetchall()
        grouped = {}
        for row in rows:
            grouped.setdefault(row["movie_id"], []).append(_show_dict(row))
        return grouped

    @staticmethod
    def list_all(conn, movie_id=None):
        query = _SHOW_SELECT
        params = ()
        if movie_id is not None:
            query += " WHERE s.movie_id = ?"
            params = (movie_id,)
        rows = conn.execute(query + " ORDER BY s.show_date, s.show_time, r.room_number", params).fetchall()
        return [_show_dict(row) for row in rows]

    @staticmethod
    def find_in_room_at(conn, room_id, show_date, show_time):
        return conn.execute(
            "SELECT show_id FROM shows WHERE room_id = ? AND show_date = ? AND show_time = ?",
            (room_id, show_date, show_time),
        ).fetchone()

    @staticmethod
    def create(conn, movie_id, room_id, show_date, show_time):
        """Adds the showtime and one AVAILABLE show_seat for every seat in the showroom."""
        cursor = conn.execute(
            "INSERT INTO shows (movie_id, room_id, show_date, show_time) VALUES (?, ?, ?, ?)",
            (movie_id, room_id, show_date, show_time),
        )
        show_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO show_seats (show_id, room_id, seat_id, status) "
            "SELECT ?, room_id, seat_id, 'AVAILABLE' FROM seats WHERE room_id = ?",
            (show_id, room_id),
        )
        return show_id


def _placeholders(items):
    return ", ".join("?" for _ in items)


class SeatRepository:
    """Seats of one showtime. A seat is AVAILABLE, HELD (picked by someone who hasn't paid yet) or BOOKED.

    A HELD seat whose held_until has passed counts as AVAILABLE again, so abandoned
    selections release themselves without a background job.
    """

    @staticmethod
    def seat_map(conn, show_id, token, now_iso):
        rows = conn.execute(
            "SELECT se.seat_id, se.row_label, se.seat_number, ss.status, ss.held_by, ss.held_until "
            "FROM show_seats ss JOIN seats se ON se.seat_id = ss.seat_id "
            "WHERE ss.show_id = ? ORDER BY se.row_label, se.seat_number",
            (show_id,),
        ).fetchall()
        seats = []
        for row in rows:
            status = row["status"]
            if status == "HELD":
                if row["held_until"] is None or row["held_until"] <= now_iso:
                    status = "AVAILABLE"
                elif token and row["held_by"] == token:
                    status = "SELECTED"
            seats.append({
                "seatId": row["seat_id"],
                "row": row["row_label"],
                "number": row["seat_number"],
                "label": f"{row['row_label']}{row['seat_number']}",
                "status": status,
            })
        return seats

    @staticmethod
    def labels(conn, show_id, seat_ids):
        """{seat_id: 'A5'} for those seat ids that belong to this showtime."""
        if not seat_ids:
            return {}
        rows = conn.execute(
            "SELECT se.seat_id, se.row_label, se.seat_number FROM show_seats ss "
            f"JOIN seats se ON se.seat_id = ss.seat_id WHERE ss.show_id = ? AND ss.seat_id IN ({_placeholders(seat_ids)})",
            (show_id, *seat_ids),
        ).fetchall()
        return {row["seat_id"]: f"{row['row_label']}{row['seat_number']}" for row in rows}

    @staticmethod
    def release_for_token(conn, token):
        conn.execute(
            "UPDATE show_seats SET status = 'AVAILABLE', held_by = NULL, held_until = NULL "
            "WHERE held_by = ? AND status = 'HELD'",
            (token,),
        )

    @staticmethod
    def hold(conn, show_id, seat_ids, token, until_iso, now_iso):
        """Reserve the seats for this token. Returns False if any of them is taken.

        The UPDATE only touches seats that are free right now, so two people choosing the same
        seat at the same moment can't both get it. The caller rolls back when this returns False.
        """
        cursor = conn.execute(
            "UPDATE show_seats SET status = 'HELD', held_by = ?, held_until = ? "
            f"WHERE show_id = ? AND seat_id IN ({_placeholders(seat_ids)}) "
            "AND (status = 'AVAILABLE' OR (status = 'HELD' AND held_until <= ?))",
            (token, until_iso, show_id, *seat_ids, now_iso),
        )
        return cursor.rowcount == len(seat_ids)

    @staticmethod
    def still_held(conn, show_id, seat_ids, token, now_iso):
        """True if every one of these seats is still held by this token and the hold hasn't expired."""
        count = conn.execute(
            f"SELECT COUNT(*) FROM show_seats WHERE show_id = ? AND seat_id IN ({_placeholders(seat_ids)}) "
            "AND status = 'HELD' AND held_by = ? AND held_until > ?",
            (show_id, *seat_ids, token, now_iso),
        ).fetchone()[0]
        return count == len(seat_ids)

    @staticmethod
    def renew(conn, show_id, token, until_iso, now_iso):
        conn.execute(
            "UPDATE show_seats SET held_until = ? WHERE show_id = ? AND held_by = ? "
            "AND status = 'HELD' AND held_until > ?",
            (until_iso, show_id, token, now_iso),
        )


class TicketTypeRepository:
    @staticmethod
    def all(conn):
        """{'ADULT': {'id': 1, 'price': 12.0}, 'CHILD': ..., 'SENIOR': ...}"""
        rows = conn.execute("SELECT ticket_type_id, category, price FROM ticket_types ORDER BY ticket_type_id").fetchall()
        return {row["category"]: {"id": row["ticket_type_id"], "price": row["price"]} for row in rows}


class PromotionRepository:
    @staticmethod
    def exists(conn, promo_code):
        return conn.execute("SELECT 1 FROM promotions WHERE promo_code = ?", (promo_code,)).fetchone() is not None

    @staticmethod
    def create(conn, promotion):
        conn.execute(
            "INSERT INTO promotions (promo_code, description, discount_rate, start_date, end_date) VALUES (?, ?, ?, ?, ?)",
            (
                promotion["promoCode"], promotion["description"], promotion["discountPercent"] / 100,
                promotion["startDate"], promotion["endDate"],
            ),
        )

    @staticmethod
    def list_all(conn):
        rows = conn.execute(
            "SELECT promo_code, description, discount_rate, start_date, end_date FROM promotions "
            "ORDER BY start_date DESC, promo_code"
        ).fetchall()
        return [
            {
                "promoCode": row["promo_code"],
                "description": row["description"],
                "discountPercent": round(row["discount_rate"] * 100),
                "startDate": row["start_date"],
                "endDate": row["end_date"],
            }
            for row in rows
        ]

    @staticmethod
    def subscribers(conn):
        """Active customers who opted in to promotion emails. Nobody else is ever emailed a promotion."""
        rows = conn.execute(
            "SELECT u.first_name, u.email FROM users u JOIN customers c ON c.customer_id = u.user_id "
            "WHERE u.role = 'CUSTOMER' AND u.promo_opt_in = 1 AND c.status = 'ACTIVE' ORDER BY u.user_id"
        ).fetchall()
        return [{"firstName": row["first_name"], "email": row["email"]} for row in rows]


def expiry(minutes=0, hours=0):
    return timedelta(minutes=minutes, hours=hours)


class ShowtimeRepository:
    """Only database operations. Business validation belongs in the service."""

    @staticmethod
    def rooms(conn):
        return [dict(r) for r in conn.execute('SELECT room_id, room_number, theater_id FROM showrooms ORDER BY room_id')]

    @staticmethod
    def list(conn, movie_id=None):
        query = """SELECT s.show_id, s.movie_id, m.title AS movie_title, s.room_id,
                          r.room_number, s.show_date, s.show_time
                   FROM shows s JOIN movies m ON m.id=s.movie_id
                   JOIN showrooms r ON r.room_id=s.room_id"""
        if movie_id is not None:
            query += ' WHERE s.movie_id=?'
            args = (movie_id,)
        else:
            args = ()
        query += ' ORDER BY s.show_date, s.show_time, s.room_id'
        return [dict(r) for r in conn.execute(query, args)]

    @staticmethod
    def create(conn, movie_id, room_id, show_date, show_time):
        cursor = conn.execute('INSERT INTO shows(movie_id,room_id,show_date,show_time) VALUES (?,?,?,?)',
                              (movie_id, room_id, show_date, show_time))
        show_id = cursor.lastrowid
        conn.execute('''INSERT INTO show_seats(show_id,room_id,seat_id)
                        SELECT ?, ?, seat_id FROM seats WHERE room_id=?''', (show_id, room_id, room_id))
        return show_id

    @staticmethod
    def seat_map(conn, show_id):
        show = conn.execute('SELECT show_id, movie_id, room_id, show_date, show_time FROM shows WHERE show_id=?', (show_id,)).fetchone()
        if show is None:
            return None
        seats = conn.execute('''SELECT ss.show_seat_id, s.row_label, s.seat_number, ss.status
                                FROM show_seats ss JOIN seats s ON s.seat_id=ss.seat_id
                                WHERE ss.show_id=? ORDER BY s.row_label, s.seat_number''', (show_id,)).fetchall()
        return {'show': dict(show), 'seats': [dict(r) for r in seats]}

    @staticmethod
    def conflicts(conn, room_id, show_date, start_time, duration_minutes, buffer_minutes=15):
        """Uses movie runtime to guard overlapping performances in one showroom."""
        from datetime import datetime, timedelta
        start = datetime.fromisoformat(show_date + 'T' + start_time)
        finish = start + timedelta(minutes=duration_minutes + buffer_minutes)
        existing = conn.execute('''SELECT s.show_time, m.runtime FROM shows s
                                   JOIN movies m ON m.id=s.movie_id
                                   WHERE s.room_id=? AND s.show_date=?''', (room_id, show_date)).fetchall()
        for row in existing:
            mins = parse_runtime_minutes(row['runtime'])
            if mins is None:
                return True  # don't permit unsafe overlap if runtime unknown
            other_start = datetime.fromisoformat(show_date + 'T' + row['show_time'])
            other_finish = other_start + timedelta(minutes=mins + buffer_minutes)
            if start < other_finish and other_start < finish:
                return True
        return False



def parse_runtime_minutes(value):
    """Accept '2 hr 4 min', '3 hr', or integer-minute runtimes."""
    import re
    if value is None:
        return None
    text = str(value).strip().lower()
    if text.isdigit():
        return int(text) if int(text)>0 else None
    match = re.fullmatch(r'(?:(\d+)\s*(?:hr|hour|hours|h))?\s*(?:(\d+)\s*(?:min|minutes|m))?', text)
    if not match or not any(match.groups()):
        return None
    result = int(match.group(1) or 0)*60+int(match.group(2) or 0)
    return result if result>0 else None


class BookingRepository:
    @staticmethod
    def types(conn):
        return [dict(r) for r in conn.execute('SELECT ticket_type_id, category, price FROM ticket_types ORDER BY ticket_type_id')]

    @staticmethod
    def save_draft(conn, draft_id, show_id, selected_seats, types, customer_id=None, email=None):
        import json
        from datetime import datetime, timedelta, timezone
        expires = (datetime.now(timezone.utc)+timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''INSERT INTO booking_drafts(draft_id,show_id,seats_json,types_json,customer_id,email,expires_at)
                        VALUES(?,?,?,?,?,?,?)''', (draft_id,show_id,json.dumps(selected_seats),json.dumps(types),customer_id,email,expires))

    @staticmethod
    def get_draft(conn, draft_id):
        import json
        row = conn.execute("SELECT * FROM booking_drafts WHERE draft_id=? AND expires_at > datetime('now')", (draft_id,)).fetchone()
        if row is None: return None
        result = dict(row)
        result['seats'] = json.loads(result.pop('seats_json'))
        result['types'] = json.loads(result.pop('types_json'))
        return result
