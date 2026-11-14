"""Test cases: scheduling showtimes (conflicts, validation) and showtime visibility for customers."""
from datetime import date, timedelta

from backend.tests.helpers import ApiTestCase, make_customer, tomorrow


class ShowroomTests(ApiTestCase):
    def test_at_least_three_showrooms_with_seats(self):
        rooms = self.admin_client().get("/api/admin/showrooms").get_json()
        self.assertGreaterEqual(len(rooms), 3)
        self.assertEqual([room["capacity"] for room in rooms[:3]], [80, 48, 120])
        self.assertEqual({room["name"] for room in rooms[:3]}, {"Showroom 1", "Showroom 2", "Showroom 3"})

    def test_showrooms_report_availability_for_a_date_and_time(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        slot = {"date": tomorrow(), "time": "10:10"}
        admin.post("/api/admin/showtimes", json={"movieId": movie["id"], "showroomId": 1, **slot})
        rooms = admin.get(f"/api/admin/showrooms?date={slot['date']}&time={slot['time']}").get_json()
        busy = {room["id"]: room["available"] for room in rooms}
        self.assertFalse(busy[1])
        self.assertTrue(busy[2])

    def test_availability_check_needs_a_valid_date_and_time(self):
        response = self.admin_client().get("/api/admin/showrooms?date=not-a-date&time=25:99")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.get_json()["errors"])
        self.assertIn("time", response.get_json()["errors"])


class SchedulingTests(ApiTestCase):
    def schedule(self, client, movie_id, room_id, day, time):
        return client.post(
            "/api/admin/showtimes", json={"movieId": movie_id, "showroomId": room_id, "date": day, "time": time}
        )

    def test_only_admins_can_schedule(self):
        movie = self.movie_by_title("Clayface")
        body = {"movieId": movie["id"], "showroomId": 1, "date": tomorrow(), "time": "09:00"}
        self.assertEqual(self.client().post("/api/admin/showtimes", json=body).status_code, 401)
        make_customer("scheduler@example.com", "7065550201")
        customer = self.client()
        self.login(customer, "scheduler@example.com")
        self.assertEqual(customer.post("/api/admin/showtimes", json=body).status_code, 403)

    def test_schedule_a_showtime_and_it_is_stored(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Clayface")
        response = self.schedule(admin, movie["id"], 3, tomorrow(), "09:05")
        self.assertEqual(response.status_code, 201, response.get_json())
        showtime = response.get_json()["showtime"]
        self.assertEqual((showtime["movieTitle"], showtime["showroom"], showtime["time"]), ("Clayface", "Showroom 3", "09:05"))
        listed = admin.get(f"/api/admin/showtimes?movieId={movie['id']}").get_json()
        self.assertIn(showtime["showId"], [show["showId"] for show in listed])
        seats = self.seats_of(self.client(), showtime["showId"])
        self.assertEqual(len(seats["seats"]), 120)  # one seat record per seat in Showroom 3
        self.assertEqual(seats["counts"]["AVAILABLE"], 120)

    def test_same_showroom_same_time_is_a_conflict(self):
        admin = self.admin_client()
        first, second = self.movie_by_title("Verity"), self.movie_by_title("Clayface")
        self.assertEqual(self.schedule(admin, first["id"], 1, tomorrow(), "08:30").status_code, 201)
        clash = self.schedule(admin, second["id"], 1, tomorrow(), "08:30")
        self.assertEqual(clash.status_code, 409)
        body = clash.get_json()
        self.assertIn("Showroom 1 already has Verity", body["error"])
        self.assertIn("showroomId", body["errors"])
        free = {room["name"] for room in body["showrooms"] if room["available"]}
        self.assertEqual(free, {"Showroom 2", "Showroom 3"})

    def test_same_movie_twice_in_the_same_room_and_time_is_a_conflict(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        self.assertEqual(self.schedule(admin, movie["id"], 2, tomorrow(), "08:35").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 2, tomorrow(), "08:35").status_code, 409)

    def test_same_time_in_a_different_showroom_is_fine(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        for room_id in (1, 2, 3):
            response = self.schedule(admin, movie["id"], room_id, tomorrow(), "08:40")
            self.assertEqual(response.status_code, 201, response.get_json())

    def test_same_room_at_a_different_time_or_date_is_fine(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        self.assertEqual(self.schedule(admin, movie["id"], 1, tomorrow(), "08:45").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 1, tomorrow(), "08:46").status_code, 201)
        later = (date.today() + timedelta(days=2)).isoformat()
        self.assertEqual(self.schedule(admin, movie["id"], 1, later, "08:45").status_code, 201)

    def test_time_with_seconds_is_treated_as_the_same_slot(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        self.assertEqual(self.schedule(admin, movie["id"], 3, tomorrow(), "08:50").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 3, tomorrow(), "08:50:00").status_code, 409)

    def test_required_fields(self):
        response = self.admin_client().post("/api/admin/showtimes", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.get_json()["errors"]), {"movieId", "date", "time", "showroomId"})

    def test_invalid_values_are_rejected(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        cases = [
            ({"date": "2026-02-30"}, "date"),
            ({"date": "tomorrow"}, "date"),
            ({"time": "25:00"}, "time"),
            ({"time": "noon"}, "time"),
            ({"movieId": "abc"}, "movieId"),
            ({"showroomId": 1.5}, "showroomId"),
            ({"date": (date.today() - timedelta(days=1)).isoformat()}, "date"),  # in the past
        ]
        for override, field in cases:
            body = {"movieId": movie["id"], "showroomId": 1, "date": tomorrow(), "time": "07:07", **override}
            response = admin.post("/api/admin/showtimes", json=body)
            self.assertEqual(response.status_code, 400, (override, response.get_json()))
            self.assertIn(field, response.get_json()["errors"])

    def test_unknown_movie_or_showroom(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        body = {"movieId": 99999, "showroomId": 1, "date": tomorrow(), "time": "07:08"}
        self.assertEqual(admin.post("/api/admin/showtimes", json=body).status_code, 404)
        body.update(movieId=movie["id"], showroomId=99999)
        self.assertEqual(admin.post("/api/admin/showtimes", json=body).status_code, 404)


class ShowtimeVisibilityTests(ApiTestCase):
    def test_seeded_showtimes_are_loaded_from_the_database(self):
        movies = self.client().get("/api/movies").get_json()
        seeded = {"The Odyssey", "Jaws", "The Silence of the Lambs", "Dune: Part Two", "Oppenheimer",
                  "Spider-Man: Across the Spider-Verse"}
        current = [movie for movie in movies if movie["title"] in seeded]
        self.assertEqual(len(current), 6)
        for movie in current:
            self.assertTrue(movie["showings"], f"{movie['title']} has no showtimes")
            for date_text, labels in movie["showtimes"].items():
                self.assertEqual(len(labels), sum(1 for s in movie["showings"] if s["date"] == date_text))

    def test_a_new_showtime_appears_for_customers(self):
        movie = self.movie_by_title("The Cat in the Hat")
        self.assertEqual(self.client().get(f"/api/movies/{movie['id']}/showtimes").get_json()["showtimes"], [])
        admin = self.admin_client()
        created = admin.post("/api/admin/showtimes", json={
            "movieId": movie["id"], "showroomId": 2, "date": tomorrow(), "time": "15:00"
        }).get_json()["showtime"]

        listed = self.client().get(f"/api/movies/{movie['id']}/showtimes").get_json()["showtimes"]
        self.assertEqual([show["showId"] for show in listed], [created["showId"]])
        self.assertEqual(listed[0]["timeLabel"], "3:00 PM")
        self.assertEqual(listed[0]["showroom"], "Showroom 2")
        detail = self.client().get(f"/api/movies/{movie['id']}").get_json()
        self.assertEqual(detail["showtimes"], {tomorrow(): ["3:00 PM"]})

    def test_past_showtimes_are_hidden_from_customers(self):
        movie = self.movie_by_title("Dune: Part Three")
        from backend.data_access.db import db_transaction
        from backend.data_access.repositories import ShowRepository
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        with db_transaction() as conn:
            ShowRepository.create(conn, movie["id"], 1, yesterday, "10:00")
        listed = self.client().get(f"/api/movies/{movie['id']}/showtimes").get_json()["showtimes"]
        self.assertEqual(listed, [])

    def test_unknown_movie_showtimes(self):
        self.assertEqual(self.client().get("/api/movies/99999/showtimes").status_code, 404)
