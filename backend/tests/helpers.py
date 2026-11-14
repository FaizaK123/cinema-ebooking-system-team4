"""Shared setup for the Sprint 3 test cases."""
import shutil
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from backend.data_access.db import db_transaction
from backend.data_access.repositories import UserRepository
from backend.infrastructure import config
from backend.infrastructure.security import hash_password
from backend.presentation.app import app
from backend.scripts import init_db, seed_db

PASSWORD = "Passw0rd!"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 64  # enough to look like a PNG to the upload check


def tomorrow():
    return (date.today() + timedelta(days=1)).isoformat()


def make_customer(email, phone, promo=False, status="ACTIVE"):
    with db_transaction() as conn:
        user_id = UserRepository.create_customer(
            conn, "Test", "Customer", email, phone, hash_password(PASSWORD), promo
        )
        UserRepository.set_status(conn, user_id, status)
    return user_id


def ensure_database():
    """Create the schema, showrooms and seed data in the throwaway database (once per test run)."""
    if not Path(config.DB_PATH).exists():
        init_db.main()
        seed_db.main()


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_database()
        cls.upload_dir = Path(tempfile.mkdtemp(prefix="ces-posters-"))
        cls.patches = [mock.patch.object(config, "POSTER_UPLOAD_DIR", cls.upload_dir)]
        for patch in cls.patches:
            patch.start()

    @classmethod
    def tearDownClass(cls):
        for patch in cls.patches:
            patch.stop()
        shutil.rmtree(cls.upload_dir, ignore_errors=True)

    def setUp(self):
        with db_transaction() as conn:  # every test starts with no seats held
            conn.execute("UPDATE show_seats SET status = 'AVAILABLE', held_by = NULL, held_until = NULL WHERE status = 'HELD'")

    def client(self):
        return app.test_client()

    def login(self, client, email, password=PASSWORD):
        response = client.post("/api/auth/login", json={"identifier": email, "password": password})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response

    def admin_client(self):
        client = self.client()
        self.login(client, config.ADMIN_EMAIL, config.ADMIN_PASSWORD)
        return client

    def movie_by_title(self, title):
        movies = self.client().get("/api/movies").get_json()
        return next(movie for movie in movies if movie["title"] == title)

    def upcoming_show(self, index=0):
        """An upcoming seeded showtime (the same one every run for a given index)."""
        movies = self.client().get("/api/movies").get_json()
        shows = [show for movie in movies if movie["isCurrent"] for show in movie["showings"]]
        return shows[index]

    def seats_of(self, client, show_id):
        return client.get(f"/api/shows/{show_id}/seats").get_json()

    def free_seat_ids(self, client, show_id, count):
        seats = [seat for seat in self.seats_of(client, show_id)["seats"] if seat["status"] == "AVAILABLE"]
        self.assertGreaterEqual(len(seats), count)
        return [seat["seatId"] for seat in seats[:count]]
