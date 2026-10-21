PRAGMA foreign_keys = ON;
-- Existing movies table is preserved. This definition applies only to new databases.
CREATE TABLE IF NOT EXISTS movies (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, genre TEXT NOT NULL,
 rating TEXT, description TEXT, poster TEXT, trailer TEXT,
 status TEXT NOT NULL CHECK(status IN ('CURRENTLY_RUNNING','COMING_SOON')),
 release_date TEXT, runtime TEXT
);
CREATE TABLE IF NOT EXISTS users (
 user_id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, phone_num TEXT,
 role TEXT NOT NULL DEFAULT 'CUSTOMER' CHECK(role IN ('CUSTOMER','ADMIN'))
);
CREATE TABLE IF NOT EXISTS customers (
 customer_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
 status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE','INACTIVE','SUSPENDED'))
);
CREATE TABLE IF NOT EXISTS admins (
 admin_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS addresses (
 address_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 street TEXT NOT NULL, city TEXT NOT NULL, state TEXT NOT NULL, zip TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_cards (
 card_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 card_brand TEXT, last_four TEXT NOT NULL CHECK(length(last_four)=4),
 expiration_month INTEGER NOT NULL CHECK(expiration_month BETWEEN 1 AND 12),
 expiration_year INTEGER NOT NULL CHECK(expiration_year BETWEEN 2000 AND 2200),
 card_token TEXT UNIQUE
);
-- Never store card CVV or raw card number in this database.
CREATE TABLE IF NOT EXISTS theaters (
 theater_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS showrooms (
 room_id INTEGER PRIMARY KEY, theater_id INTEGER NOT NULL REFERENCES theaters(theater_id),
 room_number TEXT NOT NULL, UNIQUE(theater_id,room_number)
);
CREATE TABLE IF NOT EXISTS seats (
 seat_id INTEGER PRIMARY KEY, room_id INTEGER NOT NULL REFERENCES showrooms(room_id),
 row_label TEXT NOT NULL, seat_number INTEGER NOT NULL CHECK(seat_number>0),
 UNIQUE(room_id,row_label,seat_number), UNIQUE(seat_id,room_id)
);
CREATE TABLE IF NOT EXISTS shows (
 show_id INTEGER PRIMARY KEY, movie_id INTEGER NOT NULL REFERENCES movies(id),
 room_id INTEGER NOT NULL REFERENCES showrooms(room_id),
 show_date TEXT NOT NULL, show_time TEXT NOT NULL,
 UNIQUE(room_id,show_date,show_time), UNIQUE(show_id,room_id)
);
CREATE TABLE IF NOT EXISTS show_seats (
 show_seat_id INTEGER PRIMARY KEY, show_id INTEGER NOT NULL, room_id INTEGER NOT NULL,
 seat_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'AVAILABLE'
 CHECK(status IN ('AVAILABLE','HELD','BOOKED')),
 FOREIGN KEY(show_id,room_id) REFERENCES shows(show_id,room_id),
 FOREIGN KEY(seat_id,room_id) REFERENCES seats(seat_id,room_id),
 UNIQUE(show_id,seat_id)
);
CREATE TABLE IF NOT EXISTS promotions (
 promo_code TEXT PRIMARY KEY, description TEXT, discount_rate REAL NOT NULL
 CHECK(discount_rate BETWEEN 0 AND 1), start_date TEXT, end_date TEXT,
 CHECK(start_date IS NULL OR end_date IS NULL OR start_date<=end_date)
);
CREATE TABLE IF NOT EXISTS bookings (
 booking_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
 booking_date TEXT NOT NULL DEFAULT (date('now')),
 status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','CONFIRMED','CANCELLED')),
 promo_code TEXT REFERENCES promotions(promo_code), total_amount REAL NOT NULL DEFAULT 0 CHECK(total_amount>=0)
);
CREATE TABLE IF NOT EXISTS ticket_types (
 ticket_type_id INTEGER PRIMARY KEY, category TEXT NOT NULL UNIQUE,
 price REAL NOT NULL CHECK(price>=0)
);
CREATE TABLE IF NOT EXISTS tickets (
 ticket_id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
 show_seat_id INTEGER NOT NULL UNIQUE REFERENCES show_seats(show_seat_id),
 ticket_type_id INTEGER NOT NULL REFERENCES ticket_types(ticket_type_id),
 price_paid REAL NOT NULL CHECK(price_paid>=0)
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL REFERENCES bookings(booking_id),
 amount REAL NOT NULL CHECK(amount>=0), status TEXT NOT NULL DEFAULT 'PENDING'
 CHECK(status IN ('PENDING','PAID','FAILED','REFUNDED')),
 paid_at TEXT, provider_reference TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS preferences (
 preference_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 favorite_movie_id INTEGER REFERENCES movies(id), favorite_genre TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
 recommendation_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
 movie_id INTEGER NOT NULL REFERENCES movies(id), rec_score REAL NOT NULL CHECK(rec_score BETWEEN 0 AND 1),
 reason TEXT, UNIQUE(customer_id,movie_id)
);
CREATE INDEX IF NOT EXISTS idx_shows_movie_date ON shows(movie_id,show_date);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_show_seats_show ON show_seats(show_id,status);
