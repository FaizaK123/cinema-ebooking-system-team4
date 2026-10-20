"""Safely add the CES relational schema to the existing SQLite database.

Run from project root: python backend/init_db.py
Does not drop tables, replace movies, or alter frontend routes.
"""
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'movies.db'
SCHEMA_PATH = BASE_DIR / 'schema.sql'


def main():
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        connection.executemany(
            'INSERT OR IGNORE INTO ticket_types(category,price) VALUES (?,?)',
            [('ADULT', 12.00), ('CHILD', 8.00), ('SENIOR', 9.00)],
        )
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
