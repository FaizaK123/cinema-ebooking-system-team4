"""Create the verified demo accounts needed for the Sprint 2 demo.

Run from project root (after run.bat / run.sh has created the database once):
    python backend/seed_demo_users.py

Safe to run again: accounts that already exist are left alone.
The emails are Gmail "+" aliases of the team account, so every notice lands in that inbox.
"""
import config
from db import db_transaction
from repositories import AddressRepository, CardRepository, FavoriteRepository, UserRepository
from security import encrypt_card_number, hash_password

DEMO_PASSWORD = "DemoPass1!"

FAVORITES_USER = {
    "first_name": "Fiona", "last_name": "Favorites",
    "email": "parkercant12345+fav@gmail.com", "phone": "7065550101",
    "favorites": ["Jaws", "Dune: Part Two"],
}

CARDS_USER = {
    "first_name": "Carl", "last_name": "Cards",
    "email": "parkercant12345+cards@gmail.com", "phone": "7065550102",
    "address": {"street": "123 Main St", "city": "Athens", "state": "GA", "zip": "30602"},
    # Standard test card numbers (they pass the Luhn check but aren't real accounts).
    "cards": [
        {"cardholderName": "Carl Cards", "number": "4111111111111111", "brand": "Visa", "expMonth": 12, "expYear": 2029},
        {"cardholderName": "Carl Cards", "number": "5555555555554444", "brand": "Mastercard", "expMonth": 6, "expYear": 2030},
        {"cardholderName": "Carl Cards", "number": "378282246310005", "brand": "American Express", "expMonth": 3, "expYear": 2031},
    ],
}


def create_active_customer(conn, account):
    if UserRepository.find_by_email(conn, account["email"]):
        print(f"Already exists: {account['email']}")
        return None
    user_id = UserRepository.create_customer(
        conn, account["first_name"], account["last_name"], account["email"], account["phone"],
        hash_password(DEMO_PASSWORD), False,
    )
    UserRepository.set_status(conn, user_id, "ACTIVE")
    print(f"Created: {account['email']} / {DEMO_PASSWORD}")
    return user_id


def main():
    with db_transaction() as conn:
        user_id = create_active_customer(conn, FAVORITES_USER)
        if user_id:
            for title in FAVORITES_USER["favorites"]:
                movie = conn.execute("SELECT id FROM movies WHERE title = ?", (title,)).fetchone()
                if movie:
                    FavoriteRepository.add_movie(conn, user_id, movie["id"])

        user_id = create_active_customer(conn, CARDS_USER)
        if user_id:
            AddressRepository.save(conn, user_id, CARDS_USER["address"])
            for card in CARDS_USER["cards"]:
                CardRepository.add(conn, user_id, card, encrypt_card_number(card["number"]))
    print(f"Database: {config.DB_PATH}")


if __name__ == "__main__":
    main()
