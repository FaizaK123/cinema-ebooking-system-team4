"""Safely add the CES relational schema to the existing SQLite database.

Run from project root: python -m backend.scripts.init_db
Does not drop tables, replace movies, or alter frontend routes. Safe to run
again: it only adds what's missing (tables, columns, indexes, the admin account).
"""
import sqlite3
from contextlib import closing

from werkzeug.security import generate_password_hash

from backend.infrastructure import config

BASE_DIR = config.BASE_DIR
DB_PATH = config.DB_PATH
SCHEMA_PATH = BASE_DIR / 'data_access' / 'schema.sql'

# Columns added in Sprint 2. CREATE TABLE IF NOT EXISTS skips tables that already
# exist, so databases created before Sprint 2 get these columns added here instead.
SPRINT2_COLUMNS = [
    ('users', 'promo_opt_in', 'INTEGER NOT NULL DEFAULT 0'),
    ('payment_cards', 'cardholder_name', 'TEXT'),
    ('payment_cards', 'card_number_encrypted', 'TEXT'),
]


# Columns added in Sprint 3 (seat holds for the booking flow).
SPRINT3_COLUMNS = [
    ('show_seats', 'held_by', 'TEXT'),
    ('show_seats', 'held_until', 'TEXT'),
]

THEATER_NAME = 'Cinema E-Booking Theater'
# (room number, seat rows, seats per row). Different sizes so each showroom has its own seat map.
SHOWROOMS = [
    ('1', 8, 10),
    ('2', 6, 8),
    ('3', 10, 12),
]


def add_missing_columns(connection):
    for table, column, definition in SPRINT2_COLUMNS + SPRINT3_COLUMNS:
        existing = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if column not in existing:
            connection.execute(f'ALTER TABLE "{table}" ADD COLUMN {column} {definition}')
            print(f'Added column {table}.{column}')


def ensure_showrooms(connection):
    """Create the theater, its 3 showrooms and every seat (rows A, B, C... of numbered seats) if missing."""
    connection.execute('INSERT OR IGNORE INTO theaters (name) VALUES (?)', (THEATER_NAME,))
    theater_id = connection.execute('SELECT theater_id FROM theaters WHERE name = ?', (THEATER_NAME,)).fetchone()[0]
    for room_number, rows, seats_per_row in SHOWROOMS:
        connection.execute(
            'INSERT OR IGNORE INTO showrooms (theater_id, room_number) VALUES (?, ?)', (theater_id, room_number)
        )
        room_id = connection.execute(
            'SELECT room_id FROM showrooms WHERE theater_id = ? AND room_number = ?', (theater_id, room_number)
        ).fetchone()[0]
        connection.executemany(
            'INSERT OR IGNORE INTO seats (room_id, row_label, seat_number) VALUES (?, ?, ?)',
            [(room_id, chr(ord('A') + row), number)
             for row in range(rows) for number in range(1, seats_per_row + 1)],
        )


def ensure_admin_account(connection):
    """Create the default admin (from config / .env) if there is no admin yet."""
    if connection.execute("SELECT 1 FROM users WHERE role = 'ADMIN'").fetchone():
        return
    cursor = connection.execute(
        "INSERT INTO users (first_name, last_name, email, password_hash, role) VALUES (?, ?, ?, ?, 'ADMIN')",
        ('Site', 'Admin', config.ADMIN_EMAIL.lower(), generate_password_hash(config.ADMIN_PASSWORD)),
    )
    connection.execute('INSERT INTO admins (admin_id) VALUES (?)', (cursor.lastrowid,))
    print(f'Created admin account: {config.ADMIN_EMAIL} (password not displayed)')


def main():
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:  # commit, then close
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        add_missing_columns(connection)
        connection.executemany(
            'INSERT OR IGNORE INTO ticket_types(category,price) VALUES (?,?)',
            [('ADULT', 12.00), ('CHILD', 8.00), ('SENIOR', 9.00)],
        )
        ensure_showrooms(connection)
        ensure_admin_account(connection)
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        count = connection.execute('SELECT COUNT(*) FROM movies').fetchone()[0]
        problems = connection.execute('PRAGMA foreign_key_check').fetchall()
        if problems:
            raise RuntimeError(f'Foreign-key issues: {problems}')
        print(f'Database: {DB_PATH}')
        print(f'Tables ({len(tables)}): ' + ', '.join(row[0] for row in tables))
        print(f'Movies preserved: {count}')
        print('Foreign-key check: passed')


if __name__ == '__main__':
    main()
