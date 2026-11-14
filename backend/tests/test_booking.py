"""Test cases: the booking flow (tickets, seat map, seat selection, checkout) and seat holds."""
from backend.data_access.db import db_transaction
from backend.tests.helpers import ApiTestCase, make_customer

ADULT_2 = {"adult": 2, "child": 0, "senior": 0}


class StartBookingTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.show = self.upcoming_show()

    def start(self, client, tickets, show_id=None):
        return client.post("/api/booking/start", json={"showId": show_id or self.show["showId"], "tickets": tickets})

    def test_show_details_and_ticket_prices(self):
        data = self.client().get(f"/api/shows/{self.show['showId']}").get_json()
        self.assertEqual(data["show"]["showId"], self.show["showId"])
        self.assertEqual(data["movie"]["title"], self.show["movieTitle"])
        self.assertEqual({t["type"]: t["price"] for t in data["ticketTypes"]}, {"ADULT": 12.0, "CHILD": 8.0, "SENIOR": 9.0})
        self.assertTrue(data["bookable"])
        self.assertEqual(self.client().get("/api/shows/999999").status_code, 404)

    def test_start_with_ticket_counts_by_age_category(self):
        response = self.start(self.client(), {"adult": 2, "child": 1, "senior": 1})
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(data["ticketCount"], 4)
        self.assertEqual(data["totalBeforeTax"], 2 * 12 + 8 + 9)

    def test_invalid_ticket_counts(self):
        client = self.client()
        for tickets, field in [
            ({"adult": 0, "child": 0, "senior": 0}, "tickets"),
            ({}, "tickets"),
            ({"adult": -1}, "adult"),
            ({"adult": 1.5}, "adult"),
            ({"adult": "two"}, "adult"),
            ({"child": 101}, "child"),
        ]:
            response = self.start(client, tickets)
            self.assertEqual(response.status_code, 400, (tickets, response.get_json()))
            self.assertIn(field, response.get_json()["errors"], tickets)

    def test_missing_or_unknown_showtime(self):
        self.assertEqual(self.client().post("/api/booking/start", json={"tickets": ADULT_2}).status_code, 400)
        self.assertEqual(self.start(self.client(), ADULT_2, show_id=999999).status_code, 404)

    def test_cannot_book_more_tickets_than_there_are_seats(self):
        response = self.start(self.client(), {"adult": 100, "child": 100, "senior": 100})
        self.assertEqual(response.status_code, 409)
        self.assertIn("tickets", response.get_json()["errors"])


class SeatMapTests(ApiTestCase):
    def test_seat_map_matches_the_showroom_and_marks_booked_seats(self):
        show = self.upcoming_show()
        data = self.seats_of(self.client(), show["showId"])
        capacity = {"Showroom 1": 80, "Showroom 2": 48, "Showroom 3": 120}[show["showroom"]]
        self.assertEqual(len(data["seats"]), capacity)
        self.assertEqual(len(data["rows"]) * data["seatsPerRow"], capacity)
        self.assertGreater(data["counts"]["BOOKED"], 0)       # seeded bookings by other customers
        self.assertGreater(data["counts"]["AVAILABLE"], 0)
        self.assertEqual(sum(data["counts"].values()), capacity)
        self.assertEqual(data["seats"][0]["label"], "A1")

    def test_each_showroom_has_its_own_layout(self):
        layouts = set()
        for movie in self.client().get("/api/movies").get_json():
            for show in movie["showings"][:3]:
                data = self.seats_of(self.client(), show["showId"])
                layouts.add((show["showroom"], len(data["rows"]), data["seatsPerRow"]))
        self.assertEqual(layouts, {("Showroom 1", 8, 10), ("Showroom 2", 6, 8), ("Showroom 3", 10, 12)})


class SeatSelectionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.show = self.upcoming_show(1)

    def select(self, client, seat_ids, tickets=None, **extra):
        body = {"showId": self.show["showId"], "tickets": tickets or ADULT_2, "seatIds": seat_ids, **extra}
        return client.post("/api/booking/seats", json=body)

    def test_select_seats_without_logging_in(self):
        client = self.client()
        seat_ids = self.free_seat_ids(client, self.show["showId"], 2)
        response = self.select(client, seat_ids)
        self.assertEqual(response.status_code, 200, response.get_json())
        data = response.get_json()
        self.assertEqual(len(data["seats"]), 2)
        self.assertEqual(data["totalBeforeTax"], 24.0)
        mine = [s for s in self.seats_of(client, self.show["showId"])["seats"] if s["status"] == "SELECTED"]
        self.assertEqual(sorted(s["seatId"] for s in mine), sorted(seat_ids))

    def test_two_step_flow_start_then_seats_uses_the_saved_ticket_counts(self):
        client = self.client()
        client.post("/api/booking/start", json={"showId": self.show["showId"], "tickets": {"adult": 1, "senior": 1}})
        seat_ids = self.free_seat_ids(client, self.show["showId"], 2)
        response = client.post("/api/booking/seats", json={"seatIds": seat_ids})  # no showId or tickets repeated
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["totalBeforeTax"], 12.0 + 9.0)
        wrong_count = client.post("/api/booking/seats", json={"seatIds": seat_ids[:1]})
        self.assertEqual(wrong_count.status_code, 400)

    def test_selection_must_match_the_number_of_tickets(self):
        client = self.client()
        seat_ids = self.free_seat_ids(client, self.show["showId"], 3)
        for chosen in (seat_ids[:1], seat_ids):  # too few, too many
            response = self.select(client, chosen)
            self.assertEqual(response.status_code, 400)
            self.assertIn("seats", response.get_json()["errors"])
        self.assertEqual(self.select(client, []).status_code, 400)
        self.assertEqual(self.seats_of(client, self.show["showId"])["counts"]["SELECTED"], 0)

    def test_same_seat_twice_and_bad_ids_are_rejected(self):
        client = self.client()
        seat_id = self.free_seat_ids(client, self.show["showId"], 1)[0]
        self.assertEqual(self.select(client, [seat_id, seat_id]).status_code, 400)
        self.assertEqual(self.select(client, [seat_id, "x"]).status_code, 400)
        self.assertEqual(self.select(client, [seat_id, 99999999]).status_code, 400)  # not a seat of this showroom

    def test_already_booked_seats_cannot_be_selected(self):
        client = self.client()
        seats = self.seats_of(client, self.show["showId"])["seats"]
        booked = next(seat for seat in seats if seat["status"] == "BOOKED")
        free = next(seat for seat in seats if seat["status"] == "AVAILABLE")
        response = self.select(client, [booked["seatId"], free["seatId"]])
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["unavailableSeats"], [booked["label"]])
        self.assertIn(booked["label"], response.get_json()["error"])
        after = {s["seatId"]: s["status"] for s in self.seats_of(client, self.show["showId"])["seats"]}
        self.assertEqual(after[free["seatId"]], "AVAILABLE")  # nothing was held by the failed attempt

    def test_seats_held_by_one_visitor_are_unavailable_to_others(self):
        first, second = self.client(), self.client()
        seat_ids = self.free_seat_ids(first, self.show["showId"], 2)
        self.assertEqual(self.select(first, seat_ids).status_code, 200)

        theirs = {s["seatId"]: s["status"] for s in self.seats_of(second, self.show["showId"])["seats"]}
        self.assertEqual({theirs[i] for i in seat_ids}, {"HELD"})
        response = self.select(second, seat_ids)
        self.assertEqual(response.status_code, 409)
        # the second visitor can pick other seats
        other_ids = [i for i, status in theirs.items() if status == "AVAILABLE"][:2]
        self.assertEqual(self.select(second, other_ids).status_code, 200)

    def test_changing_the_selection_releases_the_old_seats(self):
        client = self.client()
        first, second = self.free_seat_ids(client, self.show["showId"], 2), None
        self.select(client, first)
        seats = self.seats_of(client, self.show["showId"])["seats"]
        second = [s["seatId"] for s in seats if s["status"] == "AVAILABLE"][:2]
        self.assertEqual(self.select(client, second).status_code, 200)
        after = {s["seatId"]: s["status"] for s in self.seats_of(client, self.show["showId"])["seats"]}
        self.assertEqual({after[i] for i in first}, {"AVAILABLE"})
        self.assertEqual({after[i] for i in second}, {"SELECTED"})

    def test_reselecting_your_own_seats_works(self):
        client = self.client()
        seat_ids = self.free_seat_ids(client, self.show["showId"], 2)
        self.assertEqual(self.select(client, seat_ids).status_code, 200)
        self.assertEqual(self.select(client, seat_ids).status_code, 200)

    def test_expired_holds_free_the_seats(self):
        first, second = self.client(), self.client()
        seat_ids = self.free_seat_ids(first, self.show["showId"], 2)
        self.select(first, seat_ids)
        with db_transaction() as conn:
            conn.execute("UPDATE show_seats SET held_until = '2000-01-01T00:00:00.000000Z' WHERE status = 'HELD'")
        theirs = {s["seatId"]: s["status"] for s in self.seats_of(second, self.show["showId"])["seats"]}
        self.assertEqual({theirs[i] for i in seat_ids}, {"AVAILABLE"})
        self.assertEqual(self.select(second, seat_ids).status_code, 200)

    def test_cancel_releases_the_seats(self):
        client = self.client()
        seat_ids = self.free_seat_ids(client, self.show["showId"], 2)
        self.select(client, seat_ids)
        self.assertEqual(client.delete("/api/booking/current").status_code, 200)
        self.assertIsNone(client.get("/api/booking/current").get_json()["selection"])
        self.assertEqual(self.seats_of(client, self.show["showId"])["counts"]["SELECTED"], 0)

    def test_selection_survives_a_page_refresh(self):
        client = self.client()
        self.assertIsNone(client.get("/api/booking/current").get_json()["selection"])
        seat_ids = self.free_seat_ids(client, self.show["showId"], 2)
        self.select(client, seat_ids)
        selection = client.get("/api/booking/current").get_json()["selection"]
        self.assertTrue(selection["seatsReserved"])
        self.assertEqual(selection["ticketCount"], 2)


class CheckoutTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.show = self.upcoming_show(2)
        self.email = "checkout@example.com"
        if not hasattr(CheckoutTests, "customer_created"):
            make_customer(self.email, "7065550401")
            CheckoutTests.customer_created = True

    def reserve(self, client, tickets=None):
        tickets = tickets or {"adult": 2, "child": 1, "senior": 0}
        seat_ids = self.free_seat_ids(client, self.show["showId"], sum(tickets.values()))
        response = client.post(
            "/api/booking/seats", json={"showId": self.show["showId"], "tickets": tickets, "seatIds": seat_ids}
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        return seat_ids

    def test_checkout_requires_login_and_the_seats_stay_reserved_through_login(self):
        client = self.client()
        seat_ids = self.reserve(client)

        blocked = client.get("/api/booking/order-summary")
        self.assertEqual(blocked.status_code, 401)
        self.assertTrue(blocked.get_json()["loginRequired"])
        # still reserved for this visitor, and held against everyone else
        self.assertEqual(self.seats_of(self.client(), self.show["showId"])["counts"]["HELD"], 3)

        self.login(client, self.email)
        self.assertEqual(self.seats_of(client, self.show["showId"])["counts"]["SELECTED"], 3)
        summary = client.get("/api/booking/order-summary")
        self.assertEqual(summary.status_code, 200, summary.get_json())

        other = self.client()
        self.assertEqual(
            other.post("/api/booking/seats", json={
                "showId": self.show["showId"], "tickets": {"adult": 3}, "seatIds": seat_ids
            }).status_code,
            409,
        )

    def test_order_summary_contents(self):
        client = self.client()
        seat_ids = self.reserve(client, {"adult": 2, "child": 1, "senior": 0})
        self.login(client, self.email)
        data = client.get("/api/booking/order-summary").get_json()

        self.assertEqual(data["movie"]["title"], self.show["movieTitle"])
        self.assertEqual(data["show"]["date"], self.show["date"])
        self.assertEqual(data["show"]["timeLabel"], self.show["timeLabel"])
        self.assertEqual(data["show"]["showroom"], self.show["showroom"])
        self.assertEqual(sorted(seat["seatId"] for seat in data["seats"]), sorted(seat_ids))
        self.assertEqual(
            [(t["type"], t["quantity"], t["pricePerTicket"], t["lineTotal"]) for t in data["tickets"]],
            [("ADULT", 2, 12.0, 24.0), ("CHILD", 1, 8.0, 8.0)],
        )
        self.assertEqual(data["ticketCount"], 3)
        self.assertEqual(data["totalBeforeTax"], 32.0)
        self.assertEqual(data["email"], self.email)
        self.assertEqual(data["accountEmail"], self.email)
        self.assertFalse(data["emailConfirmed"])

    def test_confirm_account_email_or_enter_a_new_one(self):
        client = self.client()
        self.reserve(client)
        self.login(client, self.email)

        keep = client.post("/api/booking/email", json={})
        self.assertEqual(keep.status_code, 200)
        self.assertEqual(keep.get_json()["email"], self.email)
        self.assertTrue(keep.get_json()["usingAccountEmail"])

        new = client.post("/api/booking/email", json={"email": "  Someone.Else@Example.com "})
        self.assertEqual(new.status_code, 200)
        self.assertEqual(new.get_json()["email"], "someone.else@example.com")
        self.assertFalse(new.get_json()["usingAccountEmail"])
        summary = client.get("/api/booking/order-summary").get_json()
        self.assertEqual(summary["email"], "someone.else@example.com")
        self.assertTrue(summary["emailConfirmed"])

        for bad in ("not-an-email", "a@b", "two@@example.com", "spaces in@example.com"):
            response = client.post("/api/booking/email", json={"email": bad})
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn("email", response.get_json()["errors"])

    def test_payment_page_after_email_is_confirmed(self):
        client = self.client()
        self.reserve(client)
        self.login(client, self.email)

        early = client.get("/api/booking/payment")
        self.assertEqual(early.status_code, 409)
        self.assertTrue(early.get_json()["needsEmail"])

        client.post("/api/booking/email", json={})
        page = client.get("/api/booking/payment")
        self.assertEqual(page.status_code, 200, page.get_json())
        data = page.get_json()
        self.assertEqual(data["order"]["totalBeforeTax"], 32.0)
        self.assertEqual(data["email"], self.email)
        self.assertFalse(data["paymentProcessing"])
        self.assertEqual(data["savedCards"], [])

    def test_checkout_without_seats(self):
        client = self.client()
        self.login(client, self.email)
        for path in ("/api/booking/order-summary", "/api/booking/payment"):
            response = client.get(path)
            self.assertEqual(response.status_code, 409)
            self.assertTrue(response.get_json()["noSelection"])
        self.assertEqual(client.post("/api/booking/email", json={}).status_code, 409)

    def test_expired_reservation_is_reported_at_checkout(self):
        client = self.client()
        self.reserve(client)
        self.login(client, self.email)
        with db_transaction() as conn:
            conn.execute("UPDATE show_seats SET held_until = '2000-01-01T00:00:00.000000Z' WHERE status = 'HELD'")
        response = client.get("/api/booking/order-summary")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.get_json()["expired"])

    def test_each_checkout_step_renews_the_hold(self):
        client = self.client()
        self.reserve(client)
        self.login(client, self.email)
        soon = "2000-01-01T00:00:00.000000Z"
        with db_transaction() as conn:
            conn.execute("UPDATE show_seats SET held_until = '2999-01-01T00:00:00.000000Z' WHERE status = 'HELD'")
        client.get("/api/booking/order-summary")
        with db_transaction() as conn:
            until = conn.execute("SELECT MAX(held_until) FROM show_seats WHERE status = 'HELD'").fetchone()[0]
        self.assertLess(until, "2999-01-01T00:00:00.000000Z")  # pulled back to now + the hold time
        self.assertGreater(until, soon)

    def test_admins_cannot_check_out(self):
        client = self.admin_client()
        self.assertEqual(client.get("/api/booking/order-summary").status_code, 403)

    def test_logging_out_releases_the_seats(self):
        client = self.client()
        self.reserve(client)
        self.login(client, self.email)
        client.post("/api/auth/logout")
        self.assertEqual(self.seats_of(self.client(), self.show["showId"])["counts"]["HELD"], 0)
        self.assertIsNone(client.get("/api/booking/current").get_json()["selection"])
