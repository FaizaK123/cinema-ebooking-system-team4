"""Test cases: promotions (validation) and emailing them to subscribed customers only."""
from datetime import date, timedelta
from unittest import mock

from backend.tests.helpers import ApiTestCase, make_customer


def promotion(**overrides):
    body = {
        "promoCode": "WINTER25",
        "discountPercent": 25,
        "description": "25% off every ticket this winter.",
        "startDate": date.today().isoformat(),
        "endDate": (date.today() + timedelta(days=30)).isoformat(),
        "emailSubject": "Winter savings at CES",
        "emailBody": "Come see a movie and save 25%.",
    }
    body.update(overrides)
    return body


class PromotionTests(ApiTestCase):
    def test_only_admins_can_add_promotions(self):
        self.assertEqual(self.client().post("/api/admin/promotions", json=promotion()).status_code, 401)

    def test_promotion_is_emailed_to_subscribed_customers_only(self):
        make_customer("promo-yes@example.com", "7065550501", promo=True)
        make_customer("promo-no@example.com", "7065550502", promo=False)
        make_customer("promo-unverified@example.com", "7065550503", promo=True, status="INACTIVE")
        with mock.patch("backend.infrastructure.email_service.EmailService.send", return_value=True) as send:
            response = self.admin_client().post("/api/admin/promotions", json=promotion(promoCode="SUBS100"))
        self.assertEqual(response.status_code, 201, response.get_json())
        recipients = [call.args[0] for call in send.call_args_list]
        self.assertIn("promo-yes@example.com", recipients)
        self.assertNotIn("promo-no@example.com", recipients)
        self.assertNotIn("promo-unverified@example.com", recipients)
        self.assertNotIn("admin@ces.local", recipients)
        self.assertEqual(response.get_json()["email"]["sent"], len(recipients))
        subject, body = send.call_args_list[0].args[1:3]
        self.assertEqual(subject, "Winter savings at CES")
        self.assertIn("SUBS100", body)

    def test_promotion_is_stored(self):
        admin = self.admin_client()
        admin.post("/api/admin/promotions", json=promotion(promoCode="STORED10", discountPercent=10, sendEmail=False))
        listed = {p["promoCode"]: p for p in admin.get("/api/admin/promotions").get_json()}
        self.assertEqual(listed["STORED10"]["discountPercent"], 10)
        self.assertEqual(admin.get("/api/admin/summary").get_json()["promotions"], len(listed))

    def test_send_email_false_sends_nothing(self):
        make_customer("promo-quiet@example.com", "7065550504", promo=True)
        with mock.patch("backend.infrastructure.email_service.EmailService.send", return_value=True) as send:
            response = self.admin_client().post("/api/admin/promotions", json=promotion(promoCode="QUIET5", sendEmail=False))
        self.assertEqual(response.status_code, 201)
        send.assert_not_called()

    def test_code_is_uppercased_and_must_be_unique(self):
        admin = self.admin_client()
        first = admin.post("/api/admin/promotions", json=promotion(promoCode="unique-1", sendEmail=False))
        self.assertEqual(first.get_json()["promotion"]["promoCode"], "UNIQUE-1")
        again = admin.post("/api/admin/promotions", json=promotion(promoCode="UNIQUE-1", sendEmail=False))
        self.assertEqual(again.status_code, 409)
        self.assertIn("promoCode", again.get_json()["errors"])

    def test_required_fields(self):
        response = self.admin_client().post("/api/admin/promotions", json={})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            set(response.get_json()["errors"]),
            {"promoCode", "discountPercent", "description", "startDate", "endDate", "emailSubject", "emailBody"},
        )

    def test_invalid_values_are_rejected(self):
        admin = self.admin_client()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        cases = [
            ({"promoCode": "ab"}, "promoCode"),
            ({"promoCode": "has space"}, "promoCode"),
            ({"promoCode": "x" * 21}, "promoCode"),
            ({"discountPercent": 0}, "discountPercent"),
            ({"discountPercent": 101}, "discountPercent"),
            ({"discountPercent": 12.5}, "discountPercent"),
            ({"discountPercent": "lots"}, "discountPercent"),
            ({"description": "x" * 501}, "description"),
            ({"startDate": yesterday}, "startDate"),
            ({"startDate": "2026-02-30"}, "startDate"),
            ({"endDate": yesterday}, "endDate"),
            ({"emailSubject": "line one\nBcc: someone@example.com"}, "emailSubject"),
            ({"emailSubject": "x" * 151}, "emailSubject"),
            ({"emailBody": "x" * 5001}, "emailBody"),
            ({"sendEmail": "yes"}, "sendEmail"),
        ]
        for override, field in cases:
            response = admin.post("/api/admin/promotions", json=promotion(**{"promoCode": "VALID1", **override}))
            self.assertEqual(response.status_code, 400, (override, response.get_json()))
            self.assertIn(field, response.get_json()["errors"], override)
        listed = [p["promoCode"] for p in admin.get("/api/admin/promotions").get_json()]
        self.assertNotIn("VALID1", listed)
