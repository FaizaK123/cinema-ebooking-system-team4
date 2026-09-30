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
    ("The Odyssey", "Adventure", "R", "Odysseus faces a dangerous journey home after the Trojan War.", "images/odyssey.jpg", "https://www.youtube.com/embed/vyCVVjA28fo", "CURRENTLY_RUNNING", "2026-07-17", "2 hr 52 min"),
    ("Jaw", "Horror", "PG", "A shark terrorizes a beach town.", "images/jaws.jpg", "https://www.youtube.com/embed/U1fu_sA7XhE", "CURRENTLY_RUNNING", "1975-06-20", "2 hr 4 min"),
    ("The Silence of the Lambs", "Thriller", "R", "An FBI trainee seeks help from an imprisoned killer.", "images/silenceOfTheLambs.jpg", "https://www.youtube.com/embed/6iB21hsprAQ", "CURRENTLY_RUNNING", "1991-02-14", "1 hr 58 min"),
    ("Dune: Part Two Wow", "Sci-Fi", "PG-13", "Paul Atreides unites with Chani and the Fremen while seeking revenge for his family.", "images/dunePartTwo.jpg", "https://www.youtube.com/embed/Way9Dexny3w", "CURRENTLY_RUNNING", "2024-03-01", "2 hr 46 min"),
    ("Oppenheimer", "Drama", "R", "The story of physicist J. Robert Oppenheimer and the creation of the atomic bomb.", "images/oppenheimer.jpg", "https://www.youtube.com/embed/bK6ldnjE3Y0", "CURRENTLY_RUNNING", "2023-07-21", "3 hr"),
    ("Spider-Man: Across the Spider-Verse", "Animation", "PG", "Miles Morales travels across the multiverse and encounters a team of Spider-People.", "images/spiderVerse.jpg", "https://www.youtube.com/embed/shW9i6k8cB0", "CURRENTLY_RUNNING", "2023-06-02", "2 hr 20 min"),
    ("Verity", "Thriller", "R", "A writer discovers disturbing secrets while completing another author's unfinished work.", "images/verity.jpg", "https://www.youtube.com/embed/xdPMKhjMSFs", "COMING_SOON", "2026-10-02", "TBD"),
    ("The Cat in the Hat", "Animation", "PG", "The Cat in the Hat brings his unpredictable adventures to a new animated story.", "images/catInTheHat.jpg", "https://www.youtube.com/embed/HT5JAp5z0-o", "COMING_SOON", "2026-11-06", "TBD"),
    ("The Hunger Games: Sunrise on the Reaping", "Adventure", "TBD", "A new Hunger Games story set decades before Katniss Everdeen's rebellion.", "images/sunriseOnTheReaping.jpg", "https://www.youtube.com/embed/fS35YSjopjE", "COMING_SOON", "2026-11-20", "TBD"),
    ("Avengers: Doomsday", "Action", "TBD", "The Avengers return to face a new threat to the Marvel universe.", "images/avengersDoomsday.jpg", "https://www.youtube.com/embed/fxNh27fRdYA", "COMING_SOON", "2026-12-18", "TBD"),
    ("Dune: Part Three", "Sci-Fi", "TBD", "The next chapter in Paul Atreides' journey continues the Dune saga.", "images/dunePartThree.jpg", "https://www.youtube.com/embed/rGNc8RRggzo", "COMING_SOON", "2026-12-18", "TBD"),
    ("Clayface", "Horror", "TBD", "A new story centered on the shape-shifting DC character Clayface.", "images/clayface.jpg", "https://www.youtube.com/embed/OGO4Mqvo3jI", "COMING_SOON", "2026-10-23", "TBD"),
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