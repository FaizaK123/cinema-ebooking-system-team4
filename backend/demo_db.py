"""Read-only demonstration of database tables and relationships."""
from pathlib import Path
import sqlite3

path = Path(__file__).resolve().parent / 'movies.db'
with sqlite3.connect(path) as db:
    db.execute('PRAGMA foreign_keys=ON')
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        columns = db.execute(f'PRAGMA table_info("{name}")').fetchall()
        foreign_keys = db.execute(f'PRAGMA foreign_key_list("{name}")').fetchall()
        print(f'\n{name.upper()}')
        for c in columns:
            print(f'  {c[1]} {c[2]}' + (' PRIMARY KEY' if c[5] else '') + (' NOT NULL' if c[3] else ''))
        for fk in foreign_keys:
            print(f'  FOREIGN KEY: {fk[3]} -> {fk[2]}.{fk[4]}')
    print('\nMovies:', db.execute('SELECT COUNT(*) FROM movies').fetchone()[0])
    print('Foreign-key violations:', db.execute('PRAGMA foreign_key_check').fetchall())
