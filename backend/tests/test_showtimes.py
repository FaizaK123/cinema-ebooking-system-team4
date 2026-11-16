"""Test cases: scheduling showtimes (conflicts, validation) and showtime visibility for customers."""
from datetime import date, datetime, timedelta

from backend.tests.helpers import ApiTestCase, make_customer, tomorrow


def unseeded_day(offset=8):
    return (date.today() + timedelta(days=offset)).isoformat()


class ShowroomTests(ApiTestCase):
    def test_at_least_three_showrooms_with_seats(self):
        rooms = self.admin_client().get("/api/admin/showrooms").get_json()
        self.assertGreaterEqual(len(rooms), 3)
        self.assertEqual([room["capacity"] for room in rooms[:3]], [80, 48, 120])
        self.assertEqual({room["name"] for room in rooms[:3]}, {"Showroom 1", "Showroom 2", "Showroom 3"})

    def test_showrooms_report_availability_for_a_date_and_time(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        slot = {"date": unseeded_day(8), "time": "10:10"}
        admin.post("/api/admin/showtimes", json={"movieId": movie["id"], "showroomId": 1, **slot})
        rooms = admin.get(f"/api/admin/showrooms?date={slot['date']}&time={slot['time']}").get_json()
        busy = {room["id"]: room["available"] for room in rooms}
        self.assertFalse(busy[1])
        self.assertTrue(busy[2])

    def test_showroom_availability_respects_three_hour_gap(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        day = unseeded_day(9)
        scheduled = admin.post(
            "/api/admin/showtimes",
            json={"movieId": movie["id"], "showroomId": 1, "date": day, "time": "10:10"},
        )
        self.assertEqual(scheduled.status_code, 201, scheduled.get_json())

        before_gap = admin.get(f"/api/admin/showrooms?date={day}&time=13:09").get_json()
        at_gap = admin.get(f"/api/admin/showrooms?date={day}&time=13:10").get_json()
        self.assertFalse(next(room for room in before_gap if room["id"] == 1)["available"])
        self.assertTrue(next(room for room in at_gap if room["id"] == 1)["available"])

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
        response = self.schedule(admin, movie["id"], 3, unseeded_day(10), "09:05")
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
        day = unseeded_day(11)
        self.assertEqual(self.schedule(admin, first["id"], 1, day, "08:30").status_code, 201)
        clash = self.schedule(admin, second["id"], 1, day, "08:30")
        self.assertEqual(clash.status_code, 409)
        body = clash.get_json()
        self.assertIn("Showroom 1 already has Verity", body["error"])
        self.assertIn("showroomId", body["errors"])
        free = {room["name"] for room in body["showrooms"] if room["available"]}
        self.assertEqual(free, {"Showroom 2", "Showroom 3"})

    def test_same_movie_twice_in_the_same_room_and_time_is_a_conflict(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        day = unseeded_day(12)
        self.assertEqual(self.schedule(admin, movie["id"], 2, day, "08:35").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 2, day, "08:35").status_code, 409)

    def test_same_time_in_a_different_showroom_is_fine(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        for room_id in (1, 2, 3):
            response = self.schedule(admin, movie["id"], room_id, unseeded_day(13), "08:40")
            self.assertEqual(response.status_code, 201, response.get_json())

    def test_same_room_at_a_different_time_or_date_is_fine(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        day = unseeded_day(14)
        self.assertEqual(self.schedule(admin, movie["id"], 1, day, "08:45").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 1, day, "11:45").status_code, 201)
        later = unseeded_day(20)
        self.assertEqual(self.schedule(admin, movie["id"], 1, later, "08:45").status_code, 201)

    def test_showtimes_cannot_be_less_than_three_hours_apart_across_midnight(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        day = unseeded_day(15)
        next_day = unseeded_day(16)
        self.assertEqual(self.schedule(admin, movie["id"], 2, day, "23:00").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 2, next_day, "01:59").status_code, 409)
        self.assertEqual(self.schedule(admin, movie["id"], 2, next_day, "02:00").status_code, 201)

    def test_legacy_conflicts_are_respaced_without_changing_show_ids(self):
        from backend.data_access.db import db_transaction
        from backend.data_access.repositories import ShowRepository
        from backend.scripts.seed_db import normalize_showtime_spacing

        movie = self.movie_by_title("Verity")
        day = unseeded_day(30)
        with db_transaction() as conn:
            show_ids = [
                ShowRepository.create(conn, movie["id"], 1, day, time)
                for time in ("10:00", "11:00")
            ]
            self.assertEqual(normalize_showtime_spacing(conn), 2)
            updated = [ShowRepository.find(conn, show_id) for show_id in show_ids]

        self.assertEqual([show["showId"] for show in updated], show_ids)
        starts = sorted(datetime.fromisoformat(f"{show['date']}T{show['time']}") for show in updated)
        self.assertGreaterEqual(starts[1] - starts[0], timedelta(hours=3))

    def test_time_with_seconds_is_treated_as_the_same_slot(self):
        admin = self.admin_client()
        movie = self.movie_by_title("Verity")
        day = unseeded_day(17)
        self.assertEqual(self.schedule(admin, movie["id"], 3, day, "08:50").status_code, 201)
        self.assertEqual(self.schedule(admin, movie["id"], 3, day, "08:50:00").status_code, 409)

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

        shows = [show for movie in current for show in movie["showings"]]
        by_room = {}
        for show in shows:
            by_room.setdefault(show["showroomId"], []).append(
                datetime.fromisoformat(f"{show['date']}T{show['time']}")
            )
        for room_shows in by_room.values():
            room_shows.sort()
            self.assertTrue(all(
                later - earlier >= timedelta(hours=3)
                for earlier, later in zip(room_shows, room_shows[1:])
            ))

    def test_a_new_showtime_appears_for_customers(self):
        movie = self.movie_by_title("The Cat in the Hat")
        self.assertEqual(self.client().get(f"/api/movies/{movie['id']}/showtimes").get_json()["showtimes"], [])
        admin = self.admin_client()
        day = unseeded_day(18)
        created = admin.post("/api/admin/showtimes", json={
            "movieId": movie["id"], "showroomId": 2, "date": day, "time": "15:00"
        }).get_json()["showtime"]

        listed = self.client().get(f"/api/movies/{movie['id']}/showtimes").get_json()["showtimes"]
        self.assertEqual([show["showId"] for show in listed], [created["showId"]])
        self.assertEqual(listed[0]["timeLabel"], "3:00 PM")
        self.assertEqual(listed[0]["showroom"], "Showroom 2")
        detail = self.client().get(f"/api/movies/{movie['id']}").get_json()
        self.assertEqual(detail["showtimes"], {day: ["3:00 PM"]})

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
