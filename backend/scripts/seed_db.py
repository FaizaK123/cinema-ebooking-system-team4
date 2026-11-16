import sqlite3

from backend.infrastructure.config import DB_PATH

def seed_movies():
    movies = sqlite3.connect(DB_PATH)
    cursor = movies.cursor()



    # create table

    table_creation_query = """
        CREATE TABLE IF NOT EXISTS movies (
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

    for movie in movie_rows:
        cursor.execute(
            "SELECT id FROM movies WHERE title = ?",
            (movie[0],)
        )

        if cursor.fetchone() is None:
            cursor.execute(
                """
                INSERT INTO movies
                (title, genre, rating, description, poster,
                 trailer, status, release_date, runtime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                movie
            )


    # get results and clean

    cursor.execute("SELECT * FROM movies")

    results = cursor.fetchall()
    print(f'Seeded catalog: {len(results)} movies')

    movies.commit()
    movies.close()


# Sprint 3 test fixtures: deterministic seed so rerunning the script won't duplicate rooms.
from datetime import date, timedelta
from backend.data_access.db import db_transaction


def seed_sprint3():
    with db_transaction() as conn:
        conn.execute("INSERT OR IGNORE INTO theaters(name) VALUES ('CES Demo Theater')")
        theater_id = conn.execute("SELECT theater_id FROM theaters WHERE name = ?", ('CES Demo Theater',)).fetchone()[0]
        layouts = [('Screen 1', 5, 8), ('Screen 2', 6, 10), ('Screen 3', 8, 10)]
        room_ids = []
        for room_name, rows, columns in layouts:
            conn.execute('INSERT OR IGNORE INTO showrooms(theater_id,room_number) VALUES (?,?)', (theater_id, room_name))
            room_id = conn.execute('SELECT room_id FROM showrooms WHERE theater_id=? AND room_number=?', (theater_id, room_name)).fetchone()[0]
            room_ids.append(room_id)
            for row in range(rows):
                for column in range(1, columns + 1):
                    conn.execute('INSERT OR IGNORE INTO seats(room_id,row_label,seat_number) VALUES (?,?,?)', (room_id, chr(65+row), column))
        movies = conn.execute("SELECT id FROM movies WHERE status='CURRENTLY_RUNNING' ORDER BY id LIMIT 3").fetchall()
        if len(movies) < 3:
            print('Sprint 3: seed at least three current movies before adding showtimes')
            return
        # Different rooms at the same clock time are allowed.
        show_date = (date.today() + timedelta(days=1)).isoformat()
        for index, movie in enumerate(movies):
            room_id = room_ids[index]
            conn.execute('INSERT OR IGNORE INTO shows(movie_id,room_id,show_date,show_time) VALUES (?,?,?,?)',
                         (movie[0], room_id, show_date, '14:00'))
            show_id = conn.execute('SELECT show_id FROM shows WHERE room_id=? AND show_date=? AND show_time=?',
                                   (room_id, show_date, '14:00')).fetchone()[0]
            conn.execute('''INSERT OR IGNORE INTO show_seats(show_id,room_id,seat_id)
                             SELECT ?, ?, seat_id FROM seats WHERE room_id=?''', (show_id, room_id, room_id))
        # One deliberately booked seat in the first demo screening for UI testing.
        # This account cannot log in and is solely fixture data.
        email = 'occupied-seat-fixture@example.invalid'
        conn.execute("""INSERT OR IGNORE INTO users(first_name,last_name,email,password_hash,role)
                        VALUES('Demo','Occupant',?,'fixture-not-a-real-password','CUSTOMER')""", (email,))
        user_id = conn.execute('SELECT user_id FROM users WHERE email=?', (email,)).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO customers(customer_id,status) VALUES (?,'ACTIVE')", (user_id,))
        first_show_id = conn.execute('SELECT show_id FROM shows ORDER BY show_id LIMIT 1').fetchone()[0]
        first_seat_id = conn.execute('SELECT show_seat_id FROM show_seats WHERE show_id=? ORDER BY show_seat_id LIMIT 1',
                                     (first_show_id,)).fetchone()[0]
        booking = conn.execute('''SELECT b.booking_id FROM bookings b JOIN tickets t ON t.booking_id=b.booking_id
                                  WHERE t.show_seat_id=?''', (first_seat_id,)).fetchone()
        if booking is None:
            cursor = conn.execute("INSERT INTO bookings(customer_id,status,total_amount) VALUES (?,'CONFIRMED',12)", (user_id,))
            ticket_type = conn.execute("SELECT ticket_type_id FROM ticket_types WHERE category='ADULT'").fetchone()[0]
            conn.execute('INSERT INTO tickets(booking_id,show_seat_id,ticket_type_id,price_paid) VALUES (?,?,?,12)',
                         (cursor.lastrowid,first_seat_id,ticket_type))
        conn.execute("UPDATE show_seats SET status='BOOKED' WHERE show_seat_id=?", (first_seat_id,))
    print('Sprint 3 seed: 3 rooms and their seats, plus 3 demo showtimes, ready')


if __name__ == '__main__':
    seed_movies()
    seed_sprint3()
