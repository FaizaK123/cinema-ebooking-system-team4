import sqlite3
import os

# TEMPORARY DB for creation of backend. Connection will be replaced with REAL DB.

# define connection and cursor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "movies.db")


movies = sqlite3.connect(DB_PATH)
cursor = movies.cursor()

# drop if exists

cursor.execute("DROP TABLE IF EXISTS movies")

# create table

table_creation_query = """
    CREATE TABLE movies (
    id INTEGER PRIMARY KEY,
    title TEXT,
    genre TEXT,
    rating TEXT,
    description TEXT,
    poster TEXT,
    trailer TEXT,
    status TEXT,
    release_date TEXT,
    runtime TEXT
    );
"""

cursor.execute(table_creation_query)

# fill table

movie_rows = [
    ("Jaws", "Horror", "PG", "A shark terrorizes a beach town.", "images/moviePoster1.jpg", "https://www.youtube.com/embed/U1fu_sA7XhE", "CURRENTLY_RUNNING", "1975-06-20", "2 hr 4 min"),
    ("The Silence of the Lambs", "Thriller", "R", "An FBI trainee seeks help from an imprisoned killer.", "images/moviePoster2.jpg", "https://www.youtube.com/embed/VIDEO_ID", "CURRENTLY_RUNNING", "1991-02-14", "1 hr 58 min"),
    ("The Odyssey", "Adventure", "R", "Odysseus struggles to return home after the Trojan War.", "images/moviePoster3.jpg", "https://www.youtube.com/embed/VIDEO_ID", "CURRENTLY_RUNNING", "2026-07-17", "2 hr 19 min"),
    ("Arrival", "Sci-Fi", "PG-13", "A linguist works to communicate with alien visitors.", "images/moviePoster2.jpg", "https://www.youtube.com/embed/VIDEO_ID", "COMING_SOON", "2026-12-24", "1 hr 56 min"),
    ("Dune", "Sci-Fi", "PG-13", "A noble family fights for control of a desert planet.", "images/moviePoster3.jpg", "https://www.youtube.com/embed/VIDEO_ID", "COMING_SOON", "2027-01-05", "2 hr 35 min"),
]

cursor.executemany(
    "INSERT INTO movies (title, genre, rating, description, poster, trailer, status, release_date, runtime) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    movie_rows
)


# get results and clean

cursor.execute("SELECT * FROM movies")

results = cursor.fetchall()
print(results)

movies.commit()
movies.close()