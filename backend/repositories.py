"""Data access layer: every SQL query for users, addresses, cards, tokens and favorites.

Routes call these classes instead of writing SQL themselves, so the database
details live in one place. Each method takes an open connection, which lets a
route group several calls into one transaction.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


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
    @staticmethod
    def find(conn, movie_id):
        return conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()

    @staticmethod
    def genres(conn):
        rows = conn.execute(
            "SELECT DISTINCT genre FROM movies WHERE genre IS NOT NULL AND genre != '' ORDER BY genre"
        ).fetchall()
        return [row["genre"] for row in rows]


def expiry(minutes=0, hours=0):
    return timedelta(minutes=minutes, hours=hours)
